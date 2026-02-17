from backend.app.core.simulation_engine import SimulationEngine, SimulationEngineConfig


def _build_engine() -> SimulationEngine:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, default_phase_duration=2))
    engine.add_road("A", "B", base_time=1)
    engine.add_road("B", "C", base_time=1)
    engine.add_road("C", "D", base_time=1)
    engine.add_road("D", "E", base_time=1)
    engine.add_signal("B")
    engine.add_signal("C")
    engine.add_signal("D")
    return engine


def test_engine_instantiates_graph_signals_and_ambulances() -> None:
    engine = _build_engine()
    ambulance_id = engine.spawn_ambulance("A", "C")

    assert engine.city_graph.get_intersections() != []
    assert "B" in engine.signals
    assert ambulance_id in engine.ambulances


def test_sliding_window_allows_progress_after_multi_junction_approvals() -> None:
    engine = _build_engine()
    ambulance_id = engine.spawn_ambulance("A", "E")

    for _ in range(12):
        engine.step()

    state = engine.ambulances[ambulance_id].get_state()
    assert engine.tick_count == 12
    assert state["current_node"] in {"B", "C", "D", "E"}


def test_no_deadlock_under_two_ambulance_conflict() -> None:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0))
    engine.add_road("A", "B", base_time=1)
    engine.add_road("X", "B", base_time=1)
    engine.add_road("B", "C", base_time=1)
    engine.add_road("C", "D", base_time=1)
    engine.add_signal("B")
    engine.add_signal("C")
    engine.add_signal("D")
    engine.spawn_ambulance("A", "D", ambulance_id="AMB_1")
    engine.spawn_ambulance("X", "D", ambulance_id="AMB_2")

    engine.run_for_ticks(80, sleep=False)
    assert engine.ambulances["AMB_1"].arrived is True
    assert engine.ambulances["AMB_2"].arrived is True


def test_simulation_runs_ten_minutes_without_crash() -> None:
    engine = _build_engine()
    engine.spawn_ambulance("A", "E", ambulance_id="AMB_1")
    engine.spawn_ambulance("A", "E", ambulance_id="AMB_2")

    engine.run_for_ticks(600, sleep=False)
    snapshot = engine.get_state_snapshot()

    assert snapshot["timestamp"] == 600
    assert isinstance(snapshot["metrics"], dict)
