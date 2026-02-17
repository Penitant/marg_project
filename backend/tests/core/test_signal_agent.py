from backend.app.core.signal_agent import SignalAgent


def test_queue_and_active_reservation_structure() -> None:
    agent = SignalAgent(agent_id="SIG:I1", intersection_id="I1")
    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:1",
            "target_id": "SIG:I1",
            "payload": {
                "ambulance_id": "AMB_1",
                "corridor_id": "C1",
                "priority": 0.5,
                "required_phase": "NS_GREEN",
            },
            "timestamp": 1,
        }
    )
    agent.tick(timestamp=1)

    snapshot = agent.get_snapshot()
    assert snapshot["active_reservation"] is not None
    assert isinstance(snapshot["reservation_queue"], list)


def test_hysteresis_prevents_flip_flop_displacement() -> None:
    agent = SignalAgent(agent_id="SIG:I2", intersection_id="I2", priority_hysteresis_margin=0.2)
    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:1",
            "target_id": "SIG:I2",
            "payload": {
                "ambulance_id": "AMB_1",
                "corridor_id": "C1",
                "priority": 1.0,
                "required_phase": "NS_GREEN",
            },
            "timestamp": 1,
        }
    )
    agent.tick(timestamp=1)
    agent.drain_outbox()

    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:2",
            "target_id": "SIG:I2",
            "payload": {
                "ambulance_id": "AMB_2",
                "corridor_id": "C2",
                "priority": 1.1,
                "required_phase": "EW_GREEN",
            },
            "timestamp": 2,
        }
    )
    agent.tick(timestamp=2)
    assert agent.active_reservation is not None
    assert agent.active_reservation["ambulance_id"] == "AMB_1"


def test_higher_priority_displaces_when_margin_exceeded() -> None:
    agent = SignalAgent(
        agent_id="SIG:I3",
        intersection_id="I3",
        priority_hysteresis_margin=0.05,
        min_reservation_hold_ticks=0,
    )
    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:1",
            "target_id": "SIG:I3",
            "payload": {
                "ambulance_id": "AMB_1",
                "corridor_id": "C1",
                "priority": 0.5,
                "required_phase": "NS_GREEN",
            },
            "timestamp": 1,
        }
    )
    agent.tick(timestamp=1)
    agent.drain_outbox()

    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:2",
            "target_id": "SIG:I3",
            "payload": {
                "ambulance_id": "AMB_2",
                "corridor_id": "C2",
                "priority": 0.8,
                "required_phase": "EW_GREEN",
            },
            "timestamp": 2,
        }
    )
    agent.tick(timestamp=2)
    outbox = agent.drain_outbox()
    revoke_msgs = [m for m in outbox if m["type"] == "reservation_revoke"]
    assert revoke_msgs
    assert agent.active_reservation is not None
    assert agent.active_reservation["ambulance_id"] == "AMB_2"


def test_phase_preemption_switches_to_required_green() -> None:
    agent = SignalAgent(
        agent_id="SIG:I4",
        intersection_id="I4",
        phase_duration={"NS_GREEN": 10, "NS_YELLOW": 1, "EW_GREEN": 10, "EW_YELLOW": 1},
        current_phase="NS_GREEN",
        min_reservation_hold_ticks=1,
    )
    agent.receive_message(
        {
            "type": "reservation_request",
            "sender_id": "AMB:9",
            "target_id": "SIG:I4",
            "payload": {
                "ambulance_id": "AMB_9",
                "corridor_id": "C9",
                "priority": 2.0,
                "required_phase": "EW_GREEN",
            },
            "timestamp": 1,
        }
    )

    agent.tick(timestamp=1)
    assert agent.current_phase in {"NS_GREEN", "NS_YELLOW"}
    agent.tick(timestamp=2)
    agent.tick(timestamp=3)
    assert agent.current_phase == "EW_GREEN"
