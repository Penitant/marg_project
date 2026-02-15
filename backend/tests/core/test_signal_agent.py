from backend.app.core.signal_agent import SignalAgent


def test_update_phase_cycles_when_duration_is_reached() -> None:
    agent = SignalAgent(
        intersection_id="I1",
        phase_duration={"NS_GREEN": 2, "NS_YELLOW": 1, "EW_GREEN": 2, "EW_YELLOW": 1},
    )

    assert agent.current_phase == "NS_GREEN"
    agent.update_phase()
    assert agent.current_phase == "NS_GREEN"
    agent.update_phase()
    assert agent.current_phase == "NS_YELLOW"


def test_preemption_forces_direction_and_pauses_normal_cycle() -> None:
    agent = SignalAgent(intersection_id="I2")

    agent.trigger_preemption("E")
    assert agent.emergency_override is True
    assert agent.override_direction == "E"
    assert agent.current_phase == "EW_GREEN"

    before_timer = agent.phase_timer
    agent.update_phase()
    assert agent.phase_timer == before_timer


def test_release_preemption_resets_override_and_timer() -> None:
    agent = SignalAgent(intersection_id="I3", current_phase="NS_YELLOW", phase_timer=4)
    agent.trigger_preemption("N")
    agent.current_phase = "EW_YELLOW"
    agent.phase_timer = 3

    agent.release_preemption()

    assert agent.emergency_override is False
    assert agent.override_direction is None
    assert agent.current_phase == "NS_GREEN"
    assert agent.phase_timer == 0


def test_snapshot_is_json_serializable_shape() -> None:
    agent = SignalAgent(intersection_id="I4")
    agent.set_queue("N", 5)

    snapshot = agent.get_snapshot()
    assert snapshot["intersection_id"] == "I4"
    assert snapshot["queue_by_direction"]["N"] == 5
    assert isinstance(snapshot["emergency_override"], bool)
