from datetime import datetime

from backend.app.core.simulation_engine import SimulationEngine, SimulationEngineConfig


def _build_engine() -> SimulationEngine:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, default_phase_duration=2))
    engine.add_road("A", "B", base_time=1)
    engine.add_road("B", "C", base_time=1)
    engine.add_signal("B")
    return engine


def test_engine_instantiates_graph_signals_and_ambulances() -> None:
    engine = _build_engine()
    ambulance_id = engine.spawn_ambulance("A", "C")

    assert engine.city_graph.get_intersections() != []
    assert "B" in engine.signals
    assert ambulance_id in engine.ambulances


def test_tick_moves_ambulance_and_advances_tick_count() -> None:
    engine = _build_engine()
    ambulance_id = engine.spawn_ambulance("A", "C")

    engine.tick(current_time=datetime(2026, 2, 15, 12, 0))
    state = engine.ambulances[ambulance_id].get_state()

    assert engine.tick_count == 1
    assert state["current_node"] == "B"


def test_run_for_ticks_executes_loop_without_api_integration() -> None:
    engine = _build_engine()
    engine.spawn_ambulance("A", "C")

    engine.run_for_ticks(2, sleep=False)
    snapshot = engine.get_state_snapshot()

    assert snapshot["tick"] == 2
    assert isinstance(snapshot["signals"], list)
    assert isinstance(snapshot["ambulances"], list)
    assert isinstance(snapshot["metrics"], dict)


def test_preemption_conflict_records_metric() -> None:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0))
    engine.add_road("A", "B", base_time=1)
    engine.add_road("X", "B", base_time=1)
    engine.add_road("B", "C", base_time=1)
    engine.add_signal("B")
    engine.spawn_ambulance("A", "C", ambulance_id="AMB_1")
    engine.spawn_ambulance("X", "C", ambulance_id="AMB_2")

    engine.tick(current_time=datetime(2026, 2, 15, 12, 0))
    metrics = engine.metrics_engine.export_snapshot()

    assert metrics["preemption_count"] >= 1
