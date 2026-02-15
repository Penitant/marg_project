from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol


class CityGraphCongestionPort(Protocol):
    def get_edges(self) -> list[dict]:
        pass

    def set_edge_congestion(self, edge_id: str, congestion_factor: float) -> None:
        pass


@dataclass(slots=True)
class TrafficGeneratorConfig:
    peak_multiplier: float = 1.35
    night_multiplier: float = 0.75
    random_min: float = 0.9
    random_max: float = 1.1
    min_congestion: float = 0.3
    max_congestion: float = 3.0
    force_rush_hour: bool = False


class TrafficGenerator:
    def __init__(self, city_graph: CityGraphCongestionPort, config: TrafficGeneratorConfig | None = None) -> None:
        self._city_graph = city_graph
        self._config = config or TrafficGeneratorConfig()

    def set_force_rush_hour(self, enabled: bool) -> None:
        self._config.force_rush_hour = enabled

    def update(self, current_time: datetime | None = None) -> None:
        now = current_time or datetime.now()
        tod_multiplier = self._time_of_day_multiplier(now)

        for edge in self._city_graph.get_edges():
            edge_id = edge.get("id")
            if not edge_id:
                continue

            base_congestion = float(edge.get("congestion_factor", 1.0))
            noise = random.uniform(self._config.random_min, self._config.random_max)
            next_congestion = base_congestion * tod_multiplier * noise
            next_congestion = max(self._config.min_congestion, min(self._config.max_congestion, next_congestion))

            self._city_graph.set_edge_congestion(edge_id=edge_id, congestion_factor=next_congestion)

    def _time_of_day_multiplier(self, current_time: datetime) -> float:
        if self._config.force_rush_hour:
            return self._config.peak_multiplier

        minutes = current_time.hour * 60 + current_time.minute

        morning_peak = 7 * 60 <= minutes < 10 * 60
        evening_peak = 17 * 60 <= minutes < 20 * 60
        night = minutes >= 22 * 60 or minutes < 6 * 60

        if morning_peak or evening_peak:
            return self._config.peak_multiplier
        if night:
            return self._config.night_multiplier
        return 1.0
