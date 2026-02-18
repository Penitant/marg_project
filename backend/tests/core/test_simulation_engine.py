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
    engine.add_signal("E")
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


def test_deadlock_scan_records_metric_when_cycle_present() -> None:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, deadlock_check_interval=1))
    engine.add_signal("I1")
    engine.add_signal("I2")

    signal_1 = engine.signals["I1"]
    signal_2 = engine.signals["I2"]

    signal_1.active_reservation = {
        "ambulance_id": "AMB_A",
        "corridor_id": "C_A",
        "intersection_id": "I1",
        "activated_at": 0,
        "expires_at": 999,
    }
    signal_1.reservation_queue = [
        {"ambulance_id": "AMB_B", "corridor_id": "C_B", "intersection_id": "I1", "expires_at": 999}
    ]

    signal_2.active_reservation = {
        "ambulance_id": "AMB_B",
        "corridor_id": "C_B",
        "intersection_id": "I2",
        "activated_at": 0,
        "expires_at": 999,
    }
    signal_2.reservation_queue = [
        {"ambulance_id": "AMB_A", "corridor_id": "C_A", "intersection_id": "I2", "expires_at": 999}
    ]

    engine.step()
    engine.step()
    engine.step()
    snapshot = engine.get_state_snapshot()
    metrics = snapshot["metrics"]
    assert metrics["deadlock_count"] >= 1
    assert isinstance(snapshot["deadlocks"], list)
    assert isinstance(snapshot["revocations"], list)


def test_starvation_resistance_three_competing_ambulances() -> None:
    engine = _build_engine()
    engine.spawn_ambulance("A", "E", ambulance_id="AMB_1")
    engine.spawn_ambulance("A", "E", ambulance_id="AMB_2")
    engine.spawn_ambulance("A", "E", ambulance_id="AMB_3")

    engine.run_for_ticks(2000, sleep=False)

    assert engine.ambulances["AMB_1"].arrived is True
    assert engine.ambulances["AMB_2"].arrived is True
    assert engine.ambulances["AMB_3"].arrived is True


def test_deadlock_resolution_under_load() -> None:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, deadlock_check_interval=1))
    for idx in range(50):
        node = f"N{idx}"
        next_node = f"N{idx+1}"
        engine.add_road(node, next_node, base_time=1)
        engine.add_signal(next_node)

    for idx in range(5):
        engine.spawn_ambulance("N0", "N50", ambulance_id=f"AMB_{idx+1}")

    engine.signals["N1"].active_reservation = {"ambulance_id": "AMB_1", "corridor_id": "C1", "intersection_id": "N1", "activated_at": 0, "expires_at": 9999}
    engine.signals["N1"].reservation_queue = [{"ambulance_id": "AMB_2", "corridor_id": "C2", "intersection_id": "N1", "expires_at": 9999}]
    engine.signals["N2"].active_reservation = {"ambulance_id": "AMB_2", "corridor_id": "C2", "intersection_id": "N2", "activated_at": 0, "expires_at": 9999}
    engine.signals["N2"].reservation_queue = [{"ambulance_id": "AMB_1", "corridor_id": "C1", "intersection_id": "N2", "expires_at": 9999}]

    engine.run_for_ticks(2000, sleep=False)
    metrics = engine.metrics_engine.export_snapshot()

    assert metrics["deadlock_count"] > 0
    assert metrics["deadlock_resolution_count"] > 0
    assert all(agent.arrived for agent in engine.ambulances.values())


def test_deterministic_replay_with_same_seed() -> None:
    def run_once() -> tuple[list[tuple], dict]:
        engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, deadlock_check_interval=1))
        engine.reset(seed=42)
        engine.add_road("A", "B", base_time=1)
        engine.add_road("B", "C", base_time=1)
        engine.add_road("C", "D", base_time=1)
        engine.add_road("D", "E", base_time=1)
        engine.add_signal("B")
        engine.add_signal("C")
        engine.add_signal("D")
        engine.add_signal("E")
        engine.spawn_ambulance("A", "E", ambulance_id="AMB_1")
        engine.spawn_ambulance("A", "E", ambulance_id="AMB_2")

        trace: list[tuple] = []
        for _ in range(120):
            engine.step()
            snap = engine.get_state_snapshot()
            positions = tuple((amb["id"], amb["current_node"], amb["reservation_status"]) for amb in snap["ambulances"])
            trace.append((snap["timestamp"], positions, tuple(tuple(scc) for scc in snap["deadlocks"]), tuple(snap["revocations"])))
        return trace, engine.metrics_engine.export_snapshot()

    trace1, metrics1 = run_once()
    trace2, metrics2 = run_once()

    assert trace1 == trace2
    assert metrics1 == metrics2


def test_long_horizon_stability_100_nodes_10_ambulances_5000_ticks() -> None:
    def run_once() -> tuple[list[tuple], dict, SimulationEngine]:
        engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, deadlock_check_interval=1))
        engine.reset(seed=2026)

        size = 10
        for row in range(size):
            for col in range(size):
                node = f"G{row}_{col}"
                if col + 1 < size:
                    right = f"G{row}_{col+1}"
                    engine.add_road(node, right, base_time=1)
                    engine.add_road(right, node, base_time=1)
                if row + 1 < size:
                    down = f"G{row+1}_{col}"
                    engine.add_road(node, down, base_time=1)
                    engine.add_road(down, node, base_time=1)
                engine.add_signal(node)

        source = "G0_0"
        destination = "G9_9"
        for idx in range(10):
            engine.spawn_ambulance(source, destination, ambulance_id=f"AMB_{idx+1}")

        engine.signals["G0_1"].active_reservation = {
            "ambulance_id": "AMB_1",
            "corridor_id": "C1",
            "intersection_id": "G0_1",
            "activated_at": 0,
            "expires_at": 10000,
        }
        engine.signals["G0_1"].reservation_queue = [
            {"ambulance_id": "AMB_2", "corridor_id": "C2", "intersection_id": "G0_1", "expires_at": 10000}
        ]

        engine.signals["G1_0"].active_reservation = {
            "ambulance_id": "AMB_2",
            "corridor_id": "C2",
            "intersection_id": "G1_0",
            "activated_at": 0,
            "expires_at": 10000,
        }
        engine.signals["G1_0"].reservation_queue = [
            {"ambulance_id": "AMB_1", "corridor_id": "C1", "intersection_id": "G1_0", "expires_at": 10000}
        ]

        trace: list[tuple] = []
        for _ in range(5000):
            engine.step()
            if engine.tick_count % 100 == 0:
                snapshot = engine.get_system_snapshot()
                positions = tuple((amb["id"], amb["current_node"], amb["reservation_status"]) for amb in snapshot["ambulances"])
                trace.append((snapshot["timestamp"], positions, tuple(tuple(scc) for scc in snapshot["deadlocks"]), tuple(snapshot["revocations"])))

        return trace, engine.metrics_engine.export_snapshot(), engine

    trace1, metrics1, engine1 = run_once()
    trace2, metrics2, engine2 = run_once()

    assert trace1 == trace2
    assert metrics1 == metrics2

    assert all(agent.arrived for agent in engine1.ambulances.values())
    assert metrics1["deadlock_scc_count"] > 0
    assert metrics1["deadlock_resolution_count"] >= metrics1["deadlock_scc_count"]
    assert metrics1["fairness_index"] < 1_000_000
    assert metrics1["max_wait_time"] < 5_000
    assert all(agent.arrived for agent in engine2.ambulances.values())
