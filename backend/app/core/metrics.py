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

    _ambulance_response_times: list[float] = field(default_factory=list, init=False)
    _reservation_attempts: int = field(default=0, init=False)
    _reservation_successes: int = field(default=0, init=False)
    _conflict_frequency: int = field(default=0, init=False)
    _deadlock_count: int = field(default=0, init=False)
    _queue_lengths: list[int] = field(default_factory=list, init=False)
    _corridor_stability_durations: list[float] = field(default_factory=list, init=False)

    _response_time_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _reservation_success_rate_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _queue_length_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _deadlock_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)

    def record_response_time(self, response_time: float) -> None:
        self._ambulance_response_times.append(float(response_time))

    def record_reservation_result(self, approved: bool) -> None:
        self._reservation_attempts += 1
        if approved:
            self._reservation_successes += 1

    def record_conflict(self, count: int = 1) -> None:
        self._conflict_frequency += max(0, int(count))

    def record_deadlock(self, count: int = 1) -> None:
        self._deadlock_count += max(0, int(count))

    def record_queue_length(self, queue_length: int) -> None:
        self._queue_lengths.append(max(0, int(queue_length)))

    def record_corridor_stability_duration(self, duration: float) -> None:
        self._corridor_stability_durations.append(float(duration))

    def record_tick(self, timestamp: int) -> None:
        avg_response_time = self._average(self._ambulance_response_times)
        reservation_success_rate = self._ratio(self._reservation_successes, self._reservation_attempts)
        avg_queue_length = self._average(self._queue_lengths)

        self._append_series(self._response_time_series, TimeSeriesPoint(timestamp=timestamp, value=avg_response_time))
        self._append_series(
            self._reservation_success_rate_series,
            TimeSeriesPoint(timestamp=timestamp, value=reservation_success_rate),
        )
        self._append_series(
            self._queue_length_series,
            TimeSeriesPoint(timestamp=timestamp, value=avg_queue_length),
        )
        self._append_series(
            self._deadlock_series,
            TimeSeriesPoint(timestamp=timestamp, value=float(self._deadlock_count)),
        )

    def export_snapshot(self) -> dict:
        return {
            "ambulance_response_times": list(self._ambulance_response_times),
            "avg_response_time": self._average(self._ambulance_response_times),
            "reservation_success_rate": self._ratio(self._reservation_successes, self._reservation_attempts),
            "conflict_frequency": self._conflict_frequency,
            "deadlock_count": self._deadlock_count,
            "average_queue_length": self._average(self._queue_lengths),
            "corridor_stability_duration": self._average(self._corridor_stability_durations),
            "time_series": {
                "avg_response_time": [self._point_to_dict(point) for point in self._response_time_series],
                "reservation_success_rate": [
                    self._point_to_dict(point) for point in self._reservation_success_rate_series
                ],
                "average_queue_length": [self._point_to_dict(point) for point in self._queue_length_series],
                "deadlock_count": [self._point_to_dict(point) for point in self._deadlock_series],
            },
        }

    def reset(self) -> None:
        self._ambulance_response_times.clear()
        self._reservation_attempts = 0
        self._reservation_successes = 0
        self._conflict_frequency = 0
        self._deadlock_count = 0
        self._queue_lengths.clear()
        self._corridor_stability_durations.clear()
        self._response_time_series.clear()
        self._reservation_success_rate_series.clear()
        self._queue_length_series.clear()
        self._deadlock_series.clear()

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
    def _ratio(numerator: int, denominator: int) -> float:
        if denominator <= 0:
            return 0.0
        return float(numerator) / float(denominator)

    @staticmethod
    def _latest_series_value(series: Deque[TimeSeriesPoint]) -> float:
        if not series:
            return 0.0
        return float(series[-1].value)

    @staticmethod
    def _point_to_dict(point: TimeSeriesPoint) -> dict:
        return {"timestamp": point.timestamp, "value": point.value}
