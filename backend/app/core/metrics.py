from __future__ import annotations

from collections import Counter
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
    _arrived_response_times_current_tick: list[float] = field(default_factory=list, init=False)
    _arrived_response_counter_prev_tick: Counter[float] = field(default_factory=Counter, init=False)
    _corridor_windows_seen: set[str] = field(default_factory=set, init=False)
    _corridor_windows_successful: set[str] = field(default_factory=set, init=False)
    _conflict_frequency: int = field(default=0, init=False)
    _deadlock_count: int = field(default=0, init=False)
    _deadlock_scc_count: int = field(default=0, init=False)
    _deadlock_resolution_count: int = field(default=0, init=False)
    _revocation_count: int = field(default=0, init=False)
    _queue_lengths: list[int] = field(default_factory=list, init=False)
    _corridor_stability_durations: list[float] = field(default_factory=list, init=False)
    _scc_sizes: list[int] = field(default_factory=list, init=False)
    _wait_times: list[int] = field(default_factory=list, init=False)
    _effective_priorities: list[float] = field(default_factory=list, init=False)
    _max_wait_time: int = field(default=0, init=False)

    _response_time_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _reservation_success_rate_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _queue_length_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)
    _deadlock_series: Deque[TimeSeriesPoint] = field(default_factory=deque, init=False)

    def record_response_time(self, response_time: float) -> None:
        self._arrived_response_times_current_tick.append(float(response_time))
# MARG
    def observe_corridor_window(self, corridor_id: str, status: str) -> None:
        normalized_id = str(corridor_id)
        if not normalized_id:
            return

        self._corridor_windows_seen.add(normalized_id)
        if str(status) == "approved":
            self._corridor_windows_successful.add(normalized_id)

    def record_reservation_result(self, approved: bool) -> None:
        corridor_id = f"legacy_{len(self._corridor_windows_seen)+1}"
        self.observe_corridor_window(corridor_id, "approved" if approved else "denied")

    def record_conflict(self, count: int = 1) -> None:
        self._conflict_frequency += max(0, int(count))

    def record_deadlock(self, count: int = 1) -> None:
        self._deadlock_count += max(0, int(count))

    def record_deadlock_sccs(self, sccs: list[tuple[str, ...]]) -> None:
        self._deadlock_scc_count += len(sccs)
        self._scc_sizes.extend(len(scc) for scc in sccs)

    def record_deadlock_resolution(self, count: int = 1) -> None:
        self._deadlock_resolution_count += max(0, int(count))

    def record_revocation(self, count: int = 1) -> None:
        self._revocation_count += max(0, int(count))

    def record_queue_length(self, queue_length: int) -> None:
        self._queue_lengths.append(max(0, int(queue_length)))

    def record_corridor_stability_duration(self, duration: float) -> None:
        self._corridor_stability_durations.append(float(duration))

    def record_wait_time(self, wait_time: int) -> None:
        value = max(0, int(wait_time))
        self._wait_times.append(value)
        self._max_wait_time = max(self._max_wait_time, value)

    def record_effective_priority(self, priority: float) -> None:
        self._effective_priorities.append(float(priority))

    def record_tick(self, timestamp: int) -> None:
        self._finalize_completed_ambulances_for_tick()

        avg_response_time = self._average(self._ambulance_response_times)
        successful_corridor_windows = len(self._corridor_windows_successful)
        total_corridor_windows = len(self._corridor_windows_seen)
        reservation_success_rate = self._ratio(successful_corridor_windows, total_corridor_windows)
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
        projected_response_times = self._project_completed_response_times()
        completed_count = len(projected_response_times)
        total_corridor_windows = len(self._corridor_windows_seen)
        successful_corridor_windows = len(self._corridor_windows_successful)
        reservation_success_rate = self._ratio(successful_corridor_windows, total_corridor_windows)
        return {
            "ambulance_response_times": list(projected_response_times),
            "avg_response_time": self._average(projected_response_times),
            "reservation_success_rate": reservation_success_rate,
            "conflict_frequency": self._conflict_frequency,
            "deadlock_count": self._deadlock_count,
            "deadlock_scc_count": self._deadlock_scc_count,
            "deadlock_resolution_count": self._deadlock_resolution_count,
            "revocation_count": self._revocation_count,
            "avg_scc_size": self._average_int(self._scc_sizes),
            "max_wait_time": self._max_wait_time,
            "avg_effective_priority": self._average(self._effective_priorities),
            "fairness_index": self._jains_fairness_index(projected_response_times),
            "average_queue_length": self._average(self._queue_lengths),
            "corridor_stability_duration": self._average(self._corridor_stability_durations),
            "total_corridor_windows": total_corridor_windows,
            "successful_corridor_windows": successful_corridor_windows,
            "total_reservation_requests": total_corridor_windows,
            "total_reservation_approvals": successful_corridor_windows,
            "completed_ambulance_count": completed_count,
            "response_times_list": list(projected_response_times),
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
        self._arrived_response_times_current_tick.clear()
        self._arrived_response_counter_prev_tick.clear()
        self._corridor_windows_seen.clear()
        self._corridor_windows_successful.clear()
        self._conflict_frequency = 0
        self._deadlock_count = 0
        self._deadlock_scc_count = 0
        self._deadlock_resolution_count = 0
        self._revocation_count = 0
        self._queue_lengths.clear()
        self._corridor_stability_durations.clear()
        self._scc_sizes.clear()
        self._wait_times.clear()
        self._effective_priorities.clear()
        self._max_wait_time = 0
        self._response_time_series.clear()
        self._reservation_success_rate_series.clear()
        self._queue_length_series.clear()
        self._deadlock_series.clear()

    def _finalize_completed_ambulances_for_tick(self) -> None:
        current_counter = Counter(self._arrived_response_times_current_tick)

        for response_time, current_count in current_counter.items():
            previous_count = self._arrived_response_counter_prev_tick.get(response_time, 0)
            new_completions = max(0, current_count - previous_count)
            for _ in range(new_completions):
                self._ambulance_response_times.append(float(response_time))

        self._arrived_response_counter_prev_tick = current_counter
        self._arrived_response_times_current_tick.clear()

    def _project_completed_response_times(self) -> list[float]:
        projected = list(self._ambulance_response_times)
        current_counter = Counter(self._arrived_response_times_current_tick)

        for response_time, current_count in current_counter.items():
            previous_count = self._arrived_response_counter_prev_tick.get(response_time, 0)
            new_completions = max(0, current_count - previous_count)
            for _ in range(new_completions):
                projected.append(float(response_time))

        return projected

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
    def _average_int(values: list[int]) -> float:
        if not values:
            return 0.0
        return float(sum(values)) / float(len(values))

    @staticmethod
    def _variance_int(values: list[int]) -> float:
        if not values:
            return 0.0
        mean = float(sum(values)) / float(len(values))
        return float(sum((value - mean) ** 2 for value in values)) / float(len(values))

    @staticmethod
    def _jains_fairness_index(values: list[float]) -> float:
        if len(values) < 2:
            return 1.0

        sum_values = float(sum(values))
        sum_squared = float(sum(value * value for value in values))
        denominator = float(len(values)) * sum_squared

        if denominator <= 0.0:
            return 1.0

        return (sum_values * sum_values) / denominator

    @staticmethod
    def _latest_series_value(series: Deque[TimeSeriesPoint]) -> float:
        if not series:
            return 0.0
        return float(series[-1].value)

    @staticmethod
    def _point_to_dict(point: TimeSeriesPoint) -> dict:
        return {"timestamp": point.timestamp, "value": point.value}
