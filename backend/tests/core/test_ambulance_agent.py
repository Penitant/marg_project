from backend.app.core.ambulance_agent import AmbulanceAgent
from backend.app.core.city_graph import CityGraph
from backend.config import EngineConfig


_CFG = EngineConfig()


def _build_simple_graph() -> CityGraph:
    graph = CityGraph()
    graph.add_edge("A", "B", base_time=1, congestion_factor=1.0)
    graph.add_edge("B", "C", base_time=1, congestion_factor=1.0)
    graph.add_edge("C", "D", base_time=1, congestion_factor=1.0)
    graph.add_edge("D", "E", base_time=1, congestion_factor=1.0)
    return graph


def test_sliding_window_requires_three_approvals_before_movement() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:1",
        ambulance_id="AMB_1",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )

    ambulance.tick(timestamp=1)
    requests = ambulance.drain_outbox()
    targets = {msg["target_id"] for msg in requests if msg["type"] == "reservation_request"}
    assert targets == {"SIG:B", "SIG:C", "SIG:D"}

    ambulance.tick(timestamp=2)
    assert ambulance.current_node == "A"

    for node in ("B", "C", "D"):
        ambulance.receive_message(
            {
                "type": "reservation_response",
                "sender_id": f"SIG:{node}",
                "target_id": "AMB:1",
                "payload": {
                    "approved": True,
                    "corridor_id": f"AMB_1:{node}",
                    "intersection_id": node,
                    "priority": 1.0,
                },
                "timestamp": 2,
            }
        )

    ambulance.tick(timestamp=3)
    assert ambulance.current_node == "B"


def test_revocation_is_local_only() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:2",
        ambulance_id="AMB_2",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )
    ambulance.tick(timestamp=1)
    ambulance.drain_outbox()

    for node in ("B", "C", "D"):
        ambulance.receive_message(
            {
                "type": "reservation_response",
                "sender_id": f"SIG:{node}",
                "target_id": "AMB:2",
                "payload": {
                    "approved": True,
                    "corridor_id": f"AMB_2:{node}",
                    "intersection_id": node,
                    "priority": 1.0,
                },
                "timestamp": 2,
            }
        )

    ambulance.receive_message(
        {
            "type": "reservation_revoke",
            "sender_id": "SIG:C",
            "target_id": "AMB:2",
            "payload": {"intersection_id": "C", "corridor_id": "AMB_2:C"},
            "timestamp": 2,
        }
    )
    ambulance.tick(timestamp=3)

    assert ambulance.cooldown_remaining > 0
    assert ambulance.reservation_status == "cooldown"


def test_path_locked_until_retry_threshold_then_replans() -> None:
    graph = CityGraph()
    graph.add_edge("A", "B", base_time=1, congestion_factor=1.0)
    graph.add_edge("B", "E", base_time=1, congestion_factor=1.0)
    graph.add_edge("A", "C", base_time=2, congestion_factor=1.0)
    graph.add_edge("C", "E", base_time=2, congestion_factor=1.0)

    ambulance = AmbulanceAgent(
        agent_id="AMB:3",
        ambulance_id="AMB_3",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=2,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )

    assert ambulance.planned_path == ["A", "B", "E"]
    graph.set_edge_congestion("A_B", 10.0)
    graph.set_edge_congestion("B_E", 10.0)

    ambulance.tick(timestamp=1)
    ambulance.drain_outbox()
    ambulance.receive_message(
        {
            "type": "reservation_response",
            "sender_id": "SIG:B",
            "target_id": "AMB:3",
            "payload": {
                "approved": False,
                "corridor_id": "AMB_3:B",
                "intersection_id": "B",
                "priority": 1.0,
            },
            "timestamp": 1,
        }
    )
    ambulance.tick(timestamp=2)
    assert ambulance.planned_path == ["A", "B", "E"]

    ambulance.drain_outbox()
    ambulance.receive_message(
        {
            "type": "reservation_response",
            "sender_id": "SIG:B",
            "target_id": "AMB:3",
            "payload": {
                "approved": False,
                "corridor_id": "AMB_3:B",
                "intersection_id": "B",
                "priority": 1.0,
            },
            "timestamp": 2,
        }
    )
    ambulance.tick(timestamp=3)
    assert ambulance.planned_path == ["A", "C", "E"]


def test_state_is_json_serializable_shape() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:4",
        ambulance_id="AMB_4",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )

    state = ambulance.get_state()
    assert state["id"] == "AMB_4"
    assert state["agent_id"] == "AMB:4"
    assert state["current_node"] == "A"
    assert state["destination"] == "E"
    assert isinstance(state["planned_path"], list)
    assert isinstance(state["reservation_window"], dict)
    assert isinstance(state["arrived"], bool)


def test_priority_aging_increases_effective_priority_over_time() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:5",
        ambulance_id="AMB_5",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )

    ambulance.first_reservation_request_timestamp = 0
    p1 = ambulance.compute_priority(target_path_index=1, current_timestamp=1)
    p2 = ambulance.compute_priority(target_path_index=1, current_timestamp=10)
    assert p2 > p1


def test_priority_aging_resets_after_movement() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:6",
        ambulance_id="AMB_6",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=_CFG.revocation_cooldown_ticks,
    )

    ambulance.tick(timestamp=1)
    ambulance.drain_outbox()
    for node in ("B", "C", "D"):
        ambulance.receive_message(
            {
                "type": "reservation_response",
                "sender_id": f"SIG:{node}",
                "target_id": "AMB:6",
                "payload": {
                    "approved": True,
                    "corridor_id": f"AMB_6:{node}",
                    "intersection_id": node,
                    "priority": 1.0,
                },
                "timestamp": 1,
            }
        )

    ambulance.tick(timestamp=2)
    assert ambulance.current_node == "B"
    assert ambulance.waiting_ticks == 0


def test_revocation_cooldown_blocks_requests_then_resumes() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(
        agent_id="AMB:7",
        ambulance_id="AMB_7",
        city_graph=graph,
        current_node="A",
        destination="E",
        corridor_depth=_CFG.corridor_depth,
        alpha=_CFG.alpha,
        beta=_CFG.beta,
        wait_alpha=_CFG.wait_alpha,
        max_retry_before_replan=_CFG.max_retry_before_replan,
        revocation_cooldown_ticks=2,
    )

    ambulance.receive_message(
        {
            "type": "reservation_revoke",
            "sender_id": "SIG:B",
            "target_id": "AMB:7",
            "payload": {"intersection_id": "B", "corridor_id": "AMB_7:B"},
            "timestamp": 1,
        }
    )
    ambulance.tick(timestamp=1)
    assert ambulance.reservation_status == "cooldown"
    assert not any(msg["type"] == "reservation_request" for msg in ambulance.drain_outbox())

    ambulance.tick(timestamp=2)
    assert not any(msg["type"] == "reservation_request" for msg in ambulance.drain_outbox())

    ambulance.tick(timestamp=3)
    outbox = ambulance.drain_outbox()
    assert any(msg["type"] == "reservation_request" for msg in outbox)
