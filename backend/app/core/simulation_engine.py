from __future__ import annotations

import random
import time
from dataclasses import dataclass, field
from typing import Any

from backend.app.core.ambulance_agent import AmbulanceAgent
from backend.app.core.city_graph import CityGraph
from backend.app.core.message_bus import MessageBus
from backend.app.core.metrics import MetricsEngine
from backend.app.core.signal_agent import SignalAgent
from backend.app.core.simulation_interface import SimulationInterface


@dataclass(slots=True)
class SimulationEngineConfig:
    tick_interval: float = 1.0
    default_phase_duration: int = 30
    peak_multiplier: float = 1.2


@dataclass(slots=True)
class SimulationEngine(SimulationInterface):
    config: SimulationEngineConfig = field(default_factory=SimulationEngineConfig)

    city_graph: CityGraph = field(default_factory=CityGraph, init=False)
    message_bus: MessageBus = field(default_factory=MessageBus, init=False)
    metrics_engine: MetricsEngine = field(default_factory=MetricsEngine, init=False)

    agents: dict[str, Any] = field(default_factory=dict, init=False)
    signals: dict[str, SignalAgent] = field(default_factory=dict, init=False)
    ambulances: dict[str, AmbulanceAgent] = field(default_factory=dict, init=False)

    running: bool = field(default=False, init=False)
    tick_count: int = field(default=0, init=False)

    _ambulance_seq: int = field(default=1, init=False)
    _rng: random.Random = field(default_factory=random.Random, init=False)

    def reset(self, seed: int) -> None:
        self._rng.seed(seed)
        self.message_bus.clear()
        self.metrics_engine.reset()
        self.running = False
        self.tick_count = 0
        self.agents.clear()
        self.signals.clear()
        self.ambulances.clear()
        self._ambulance_seq = 1

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
        signal = SignalAgent(
            agent_id=f"SIG:{intersection_id}",
            intersection_id=intersection_id,
            phase_duration=phase_duration,
        )
        self.signals[intersection_id] = signal
        self.register_agent(signal)

    def spawn_ambulance(self, source: str, destination: str, ambulance_id: str | None = None) -> str:
        assigned_id = ambulance_id or f"AMB_{self._ambulance_seq}"
        if assigned_id in self.ambulances:
            raise ValueError(f"Ambulance with id '{assigned_id}' already exists")

        self._ambulance_seq += 1

        ambulance = AmbulanceAgent(
            agent_id=f"AMB:{assigned_id}",
            ambulance_id=assigned_id,
            city_graph=self.city_graph,
            current_node=source,
            destination=destination,
        )
        self.ambulances[assigned_id] = ambulance
        self.register_agent(ambulance)
        return assigned_id

    def register_agent(self, agent: Any) -> None:
        self.agents[str(agent.agent_id)] = agent

    def deliver_message(self, message: dict[str, Any]) -> None:
        self.message_bus.publish(message)

    def step(self) -> None:
        self.message_bus.process(self.agents)

        for agent in self.agents.values():
            agent.tick(self.tick_count)

        for agent in self.agents.values():
            for message in agent.drain_outbox():
                self.deliver_message(message)

        self._update_congestion()
        self._record_metrics()

        self.tick_count += 1

    def run_for_ticks(self, ticks: int, sleep: bool = False) -> None:
        if ticks < 0:
            raise ValueError("ticks must be >= 0")

        for _ in range(ticks):
            self.step()
            if sleep and self.config.tick_interval > 0:
                time.sleep(self.config.tick_interval)

    def start(self, max_ticks: int | None = None) -> None:
        self.running = True
        executed = 0

        while self.running:
            self.step()
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
            "timestamp": self.tick_count,
            "running": self.running,
            "nodes": self.city_graph.get_intersections(),
            "signals": [signal.get_snapshot() for signal in self.signals.values()],
            "ambulances": [ambulance.get_state() for ambulance in self.ambulances.values()],
            "edges": self.city_graph.get_edges(),
            "reservations": self._collect_reservations(),
            "metrics": self.metrics_engine.export_snapshot(),
        }

    def _collect_reservations(self) -> list[dict]:
        reservations: list[dict] = []
        for signal in self.signals.values():
            snapshot = signal.get_snapshot()
            active = snapshot.get("active_reservation")
            if active:
                reservations.append(active)
            reservations.extend(snapshot.get("reservation_queue", []))
        return reservations

    def _update_congestion(self) -> None:
        for edge in self.city_graph.get_edges():
            edge_id = edge["id"]
            current = float(edge["congestion_factor"])
            adjustment = self._rng.uniform(-0.03, 0.03)
            self.city_graph.set_edge_congestion(edge_id, max(0.2, current + adjustment))

    def _record_metrics(self) -> None:
        for ambulance in self.ambulances.values():
            if ambulance.arrived:
                self.metrics_engine.record_response_time(ambulance.response_time)
        for signal in self.signals.values():
            total_queue = sum(signal.queue_state.values())
            self.metrics_engine.record_queue_length(total_queue)
            queued_reservations = len(signal.reservation_queue)
            if queued_reservations > 0:
                self.metrics_engine.record_conflict(queued_reservations)
        self.metrics_engine.record_tick(self.tick_count)
