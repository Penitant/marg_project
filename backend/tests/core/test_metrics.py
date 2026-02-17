from backend.app.core.metrics import MetricsConfig, MetricsEngine


def test_metrics_recording_and_snapshot_fields() -> None:
    metrics = MetricsEngine(config=MetricsConfig(rolling_window_size=3))
    metrics.record_response_time(12)
    metrics.record_response_time(18)
    metrics.record_reservation_result(True)
    metrics.record_reservation_result(False)
    metrics.record_conflict(2)
    metrics.record_deadlock(1)
    metrics.record_queue_length(7)
    metrics.record_corridor_stability_duration(5)
    metrics.record_tick(timestamp=1)

    snapshot = metrics.export_snapshot()
    assert snapshot["avg_response_time"] == 15.0
    assert snapshot["reservation_success_rate"] == 0.5
    assert snapshot["conflict_frequency"] == 2
    assert snapshot["deadlock_count"] == 1
    assert snapshot["average_queue_length"] == 7.0
    assert snapshot["corridor_stability_duration"] == 5.0


def test_metrics_rolling_window_applies_to_time_series() -> None:
    metrics = MetricsEngine(config=MetricsConfig(rolling_window_size=2))

    metrics.record_tick(timestamp=1)
    metrics.record_tick(timestamp=2)
    metrics.record_tick(timestamp=3)

    snapshot = metrics.export_snapshot()
    series = snapshot["time_series"]["avg_response_time"]
    assert len(series) == 2
    assert [point["timestamp"] for point in series] == [2, 3]


def test_metrics_reset_clears_recorded_state() -> None:
    metrics = MetricsEngine()
    metrics.record_response_time(10)
    metrics.record_reservation_result(True)
    metrics.record_conflict(1)
    metrics.record_deadlock(1)
    metrics.record_queue_length(3)
    metrics.record_corridor_stability_duration(2)
    metrics.record_tick(timestamp=5)

    metrics.reset()
    snapshot = metrics.export_snapshot()

    assert snapshot["ambulance_response_times"] == []
    assert snapshot["reservation_success_rate"] == 0.0
    assert snapshot["conflict_frequency"] == 0
    assert snapshot["deadlock_count"] == 0
    assert snapshot["average_queue_length"] == 0.0
