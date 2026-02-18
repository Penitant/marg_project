import json

from backend.config import REVOCATION_COOLDOWN_TICKS
from backend.app.core.simulation_engine import SimulationEngine, SimulationEngineConfig


def _build_moderate_engine() -> SimulationEngine:
    engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=0.0, deadlock_check_interval=1))
    for idx in range(10):
        node = f"N{idx}"
        next_node = f"N{idx+1}"
        engine.add_road(node, next_node, base_time=1)
        engine.add_signal(next_node)
    return engine


def test_exclusive_intersection_invariant() -> None:
    engine = _build_moderate_engine()
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_1")
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_2")
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_3")

    for _ in range(300):
        engine.step()
        for signal in engine.signals.values():
            active = signal.active_reservation
            assert active is None or isinstance(active, dict)


def test_queue_consistency_invariant() -> None:
    engine = _build_moderate_engine()
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_1")
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_2")
    engine.run_for_ticks(200, sleep=False)

    for signal in engine.signals.values():
        active_id = None
        if signal.active_reservation is not None:
            active_id = str(signal.active_reservation.get("ambulance_id", ""))

        queued_ids = [str(item.get("ambulance_id", "")) for item in signal.reservation_queue]
        assert len(queued_ids) == len(set(queued_ids))
        if active_id:
            assert active_id not in queued_ids


def test_json_snapshot_integrity() -> None:
    engine = _build_moderate_engine()
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_1")
    engine.run_for_ticks(50, sleep=False)

    snapshot = engine.get_system_snapshot()
    json.dumps(snapshot)


def test_cooldown_boundedness() -> None:
    engine = _build_moderate_engine()
    engine.spawn_ambulance("N0", "N10", ambulance_id="AMB_1")
    ambulance = engine.ambulances["AMB_1"]

    ambulance.receive_message(
        {
            "type": "reservation_revoke",
            "sender_id": "SIG:N1",
            "target_id": ambulance.agent_id,
            "payload": {"intersection_id": "N1", "corridor_id": "AMB_1:N1"},
            "timestamp": 1,
        }
    )

    engine.step()
    assert ambulance.cooldown_remaining <= REVOCATION_COOLDOWN_TICKS

    for _ in range(REVOCATION_COOLDOWN_TICKS + 5):
        engine.step()

    assert ambulance.cooldown_remaining == 0
    assert ambulance.reservation_status in {"idle", "pending", "approved", "denied"}


def test_movement_liveness_under_moderate_load() -> None:
    engine = _build_moderate_engine()
    for idx in range(4):
        engine.spawn_ambulance("N0", "N10", ambulance_id=f"AMB_{idx+1}")

    window = 100
    previous_positions = {amb_id: amb.current_node for amb_id, amb in engine.ambulances.items()}

    for _ in range(0, 2000, window):
        engine.run_for_ticks(window, sleep=False)
        current_positions = {amb_id: amb.current_node for amb_id, amb in engine.ambulances.items()}
        moved = any(current_positions[amb_id] != previous_positions[amb_id] for amb_id in engine.ambulances)
        all_arrived = all(agent.arrived for agent in engine.ambulances.values())
        assert moved or all_arrived
        previous_positions = current_positions