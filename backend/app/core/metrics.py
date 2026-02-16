from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from typing import Deque


@dataclass(slots=True)
class TimeSeriesPoint:
    timestamp: int
    value: float


@dataclass(slots=True)
class MetricsConfig:
    rolling_window_size: int = 300


@dataclass(slots=True)
class MetricsEngine:
    config: MetricsConfig = field(default_factory=MetricsConfig)

    _ambulance_travel_times: list[float] = field(default_factory=list, init=False)
    _vehicle_delays: list[float] = field(default_factory=list, init=False)
    _max_queue_length: int = field(default=0, init=False)
    _preemption_count: int = field(default=0, init=False)

    _congestion_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _avg_delay_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _avg_ambulance_time_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _mode_series: Deque[dict] = field(default_factory=deque, init=False)

    def record_ambulance_travel_time(self, travel_time: float) -> None:
        self._ambulance_travel_times.append(float(travel_time))

    def record_vehicle_delay(self, delay: float) -> None:
        self._vehicle_delays.append(float(delay))

    def record_queue_length(self, queue_length: int) -> None:
        self._max_queue_length = max(self._max_queue_length, int(queue_length))

    def increment_preemption_count(self, amount: int = 1) -> None:
        self._preemption_count += max(0, int(amount))

    def record_congestion_index(self, congestion_index: float, timestamp: int) -> None:
        self._append_series(self._congestion_series, TimeSeriesPoint(timestamp=timestamp, value=float(congestion_index)))

    def record_tick_summary(self, timestamp: int, mode: str = "intelligent") -> None:
        avg_delay = self._average(self._vehicle_delays)
        avg_ambulance_time = self._average(self._ambulance_travel_times)

        self._append_series(self._avg_delay_series, TimeSeriesPoint(timestamp=timestamp, value=avg_delay))
        self._append_series(
            self._avg_ambulance_time_series,
            TimeSeriesPoint(timestamp=timestamp, value=avg_ambulance_time),
        )

        self._mode_series.append(
            {
                "timestamp": int(timestamp),
                "mode": mode,
                "avg_vehicle_delay": avg_delay,
                "avg_ambulance_travel_time": avg_ambulance_time,
            }
        )
        self._trim_deque(self._mode_series)

    def export_snapshot(self) -> dict:
        return {
            "ambulance_travel_times": list(self._ambulance_travel_times),
            "avg_ambulance_travel_time": self._average(self._ambulance_travel_times),
            "vehicle_delays": list(self._vehicle_delays),
            "avg_vehicle_delay": self._average(self._vehicle_delays),
            "max_queue_length": self._max_queue_length,
            "preemption_count": self._preemption_count,
            "congestion_index": self._latest_series_value(self._congestion_series),
            "time_series": {
                "congestion_index": [self._point_to_dict(point) for point in self._congestion_series],
                "avg_vehicle_delay": [self._point_to_dict(point) for point in self._avg_delay_series],
                "avg_ambulance_travel_time": [
                    self._point_to_dict(point) for point in self._avg_ambulance_time_series
                ],
                "mode_snapshots": list(self._mode_series),
            },
        }

    def reset(self) -> None:
        self._ambulance_travel_times.clear()
        self._vehicle_delays.clear()
        self._max_queue_length = 0
        self._preemption_count = 0
        self._congestion_series.clear()
        self._avg_delay_series.clear()
        self._avg_ambulance_time_series.clear()
        self._mode_series.clear()

    def _append_series(self, series: Deque[TimeSeriesPoint], point: TimeSeriesPoint) -> None:
        series.append(point)
        self._trim_deque(series)

    def _trim_deque(self, values: Deque) -> None:
        while len(values) > self.config.rolling_window_size:
            values.popleft()

    @staticmethod
    def _average(values: list[float]) -> float:
        if not values:
            return 0.0
        return sum(values) / len(values)

    @staticmethod
    def _latest_series_value(series: Deque[TimeSeriesPoint]) -> float:
        if not series:
            return 0.0
        return float(series[-1].value)

    @staticmethod
    def _point_to_dict(point: TimeSeriesPoint) -> dict:
        return {"timestamp": point.timestamp, "value": point.value}
