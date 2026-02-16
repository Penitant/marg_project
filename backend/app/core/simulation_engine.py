from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime

from backend.app.core.ambulance_agent import AmbulanceAgent
from backend.app.core.arbitration import AmbulancePriorityInput, choose_preemption_winner
from backend.app.core.city_graph import CityGraph
from backend.app.core.metrics import MetricsEngine
from backend.app.core.signal_agent import SignalAgent
from backend.app.core.traffic_generator import TrafficGenerator, TrafficGeneratorConfig


@dataclass(slots=True)
class SimulationEngineConfig:
    tick_interval: float = 1.0
    default_phase_duration: int = 30


@dataclass(slots=True)
class SimulationEngine:
    config: SimulationEngineConfig = field(default_factory=SimulationEngineConfig)

    city_graph: CityGraph = field(default_factory=CityGraph, init=False)
    traffic_generator: TrafficGenerator = field(init=False)
    metrics_engine: MetricsEngine = field(default_factory=MetricsEngine, init=False)

    signals: dict[str, SignalAgent] = field(default_factory=dict, init=False)
    ambulances: dict[str, AmbulanceAgent] = field(default_factory=dict, init=False)

    running: bool = field(default=False, init=False)
    tick_count: int = field(default=0, init=False)

    _ambulance_seq: int = field(default=1, init=False)
    _arrival_seq: int = field(default=1, init=False)
    _arrival_order: dict[str, int] = field(default_factory=dict, init=False)

    def __post_init__(self) -> None:
        traffic_config = TrafficGeneratorConfig(random_min=1.0, random_max=1.0)
        self.traffic_generator = TrafficGenerator(self.city_graph, traffic_config)

    def add_intersection(self, intersection_id: str) -> None:
        self.city_graph.add_node(intersection_id)

    def add_road(
        self,
        source: str,
        target: str,
        base_time: float,
        congestion_factor: float = 1.0,
        capacity: float = 1.0,
        edge_id: str | None = None,
    ) -> str:
        return self.city_graph.add_edge(
            source=source,
            target=target,
            base_time=base_time,
            congestion_factor=congestion_factor,
            capacity=capacity,
            edge_id=edge_id,
        )

    def add_signal(self, intersection_id: str) -> None:
        if intersection_id in self.signals:
            return

        phase_duration = {
            "NS_GREEN": self.config.default_phase_duration,
            "NS_YELLOW": 5,
            "EW_GREEN": self.config.default_phase_duration,
            "EW_YELLOW": 5,
        }
        self.signals[intersection_id] = SignalAgent(
            intersection_id=intersection_id,
            phase_duration=phase_duration,
        )

    def spawn_ambulance(self, source: str, destination: str, ambulance_id: str | None = None) -> str:
        assigned_id = ambulance_id or f"AMB_{self._ambulance_seq}"
        if assigned_id in self.ambulances:
            raise ValueError(f"Ambulance with id '{assigned_id}' already exists")

        self._ambulance_seq += 1
        self._arrival_order[assigned_id] = self._arrival_seq
        self._arrival_seq += 1

        self.ambulances[assigned_id] = AmbulanceAgent(
            ambulance_id=assigned_id,
            city_graph=self.city_graph,
            source=source,
            destination=destination,
        )
        return assigned_id

    def tick(self, current_time: datetime | None = None) -> None:
        now = current_time or datetime.now()

        self.traffic_generator.update(now)

        for signal in self.signals.values():
            signal.update_phase()

        preemption_winners = self._resolve_conflicting_preemptions()
        if preemption_winners:
            self.metrics_engine.increment_preemption_count(len(preemption_winners))

        for ambulance in self.ambulances.values():
            was_arrived = ambulance.arrived
            ambulance.step()
            if not was_arrived and ambulance.arrived:
                self.metrics_engine.record_ambulance_travel_time(ambulance.travel_time)

        self._release_all_preemptions()

        congestion_values = [float(edge["congestion_factor"]) for edge in self.city_graph.get_edges()]
        congestion_index = sum(congestion_values) / len(congestion_values) if congestion_values else 0.0
        self.metrics_engine.record_congestion_index(congestion_index=congestion_index, timestamp=self.tick_count)
        self.metrics_engine.record_tick_summary(timestamp=self.tick_count)

        self.tick_count += 1

    def run_for_ticks(self, ticks: int, sleep: bool = False) -> None:
        if ticks < 0:
            raise ValueError("ticks must be >= 0")

        for _ in range(ticks):
            self.tick()
            if sleep and self.config.tick_interval > 0:
                time.sleep(self.config.tick_interval)

    def start(self, max_ticks: int | None = None) -> None:
        self.running = True
        executed = 0

        while self.running:
            self.tick()
            executed += 1

            if max_ticks is not None and executed >= max_ticks:
                break

            if self.config.tick_interval > 0:
                time.sleep(self.config.tick_interval)

        self.running = False

    def stop(self) -> None:
        self.running = False

    def get_state_snapshot(self) -> dict:
        return {
            "tick": self.tick_count,
            "running": self.running,
            "intersections": self.city_graph.get_intersections(),
            "signals": [signal.get_snapshot() for signal in self.signals.values()],
            "ambulances": [ambulance.get_state() for ambulance in self.ambulances.values()],
            "edges": self.city_graph.get_edges(),
            "metrics": self.metrics_engine.export_snapshot(),
        }

    def _resolve_conflicting_preemptions(self) -> set[str]:
        candidates_by_intersection: dict[str, list[AmbulancePriorityInput]] = {}

        for ambulance_id, ambulance in self.ambulances.items():
            if ambulance.arrived or len(ambulance.path) < 2:
                continue

            target_intersection = ambulance.path[1]
            if target_intersection not in self.signals:
                continue

            candidates_by_intersection.setdefault(target_intersection, []).append(
                AmbulancePriorityInput(
                    ambulance_id=ambulance_id,
                    remaining_distance=ambulance.eta,
                    arrival_order=self._arrival_order.get(ambulance_id),
                )
            )

        winners: set[str] = set()
        for intersection_id, candidates in candidates_by_intersection.items():
            if len(candidates) == 1:
                winner_id = candidates[0].ambulance_id
            else:
                decision = choose_preemption_winner(candidates)
                winner_id = decision.winner_id

            if winner_id is None:
                continue

            winners.add(winner_id)
            self.signals[intersection_id].trigger_preemption("N")

        return winners

    def _release_all_preemptions(self) -> None:
        for signal in self.signals.values():
            if signal.emergency_override:
                signal.release_preemption()
