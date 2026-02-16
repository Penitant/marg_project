from backend.app.core.metrics import MetricsConfig, MetricsEngine


def test_metrics_recording_and_snapshot_fields() -> None:
    metrics = MetricsEngine(config=MetricsConfig(rolling_window_size=3))
    metrics.record_ambulance_travel_time(12)
    metrics.record_ambulance_travel_time(18)
    metrics.record_vehicle_delay(4)
    metrics.record_queue_length(7)
    metrics.increment_preemption_count()
    metrics.record_congestion_index(1.2, timestamp=1)
    metrics.record_tick_summary(timestamp=1)

    snapshot = metrics.export_snapshot()
    assert snapshot["avg_ambulance_travel_time"] == 15.0
    assert snapshot["avg_vehicle_delay"] == 4.0
    assert snapshot["max_queue_length"] == 7
    assert snapshot["preemption_count"] == 1
    assert snapshot["congestion_index"] == 1.2
    assert len(snapshot["time_series"]["mode_snapshots"]) == 1


def test_metrics_rolling_window_applies_to_time_series() -> None:
    metrics = MetricsEngine(config=MetricsConfig(rolling_window_size=2))

    metrics.record_congestion_index(1.0, timestamp=1)
    metrics.record_congestion_index(1.1, timestamp=2)
    metrics.record_congestion_index(1.2, timestamp=3)

    snapshot = metrics.export_snapshot()
    series = snapshot["time_series"]["congestion_index"]
    assert len(series) == 2
    assert [point["timestamp"] for point in series] == [2, 3]


def test_metrics_reset_clears_recorded_state() -> None:
    metrics = MetricsEngine()
    metrics.record_ambulance_travel_time(10)
    metrics.record_vehicle_delay(2)
    metrics.record_queue_length(3)
    metrics.increment_preemption_count(2)
    metrics.record_congestion_index(1.5, timestamp=5)
    metrics.record_tick_summary(timestamp=5)

    metrics.reset()
    snapshot = metrics.export_snapshot()

    assert snapshot["ambulance_travel_times"] == []
    assert snapshot["vehicle_delays"] == []
    assert snapshot["max_queue_length"] == 0
    assert snapshot["preemption_count"] == 0
    assert snapshot["congestion_index"] == 0.0
