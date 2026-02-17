from backend.app.core.ambulance_agent import AmbulanceAgent
from backend.app.core.city_graph import CityGraph


def _build_simple_graph() -> CityGraph:
    graph = CityGraph()
    graph.add_edge("A", "B", base_time=1, congestion_factor=1.0)
    graph.add_edge("B", "C", base_time=1, congestion_factor=1.0)
    graph.add_edge("C", "D", base_time=1, congestion_factor=1.0)
    graph.add_edge("D", "E", base_time=1, congestion_factor=1.0)
    return graph


def test_sliding_window_requires_three_approvals_before_movement() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent(agent_id="AMB:1", ambulance_id="AMB_1", city_graph=graph, current_node="A", destination="E")

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
    ambulance = AmbulanceAgent(agent_id="AMB:2", ambulance_id="AMB_2", city_graph=graph, current_node="A", destination="E")
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

    assert ambulance.reservation_window["C"]["status"] in {"revoked", "pending", "denied"}
    assert ambulance.reservation_window["B"]["status"] == "approved"
    assert ambulance.reservation_window["D"]["status"] == "approved"


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
        max_retry_before_replan=2,
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
    ambulance = AmbulanceAgent(agent_id="AMB:4", ambulance_id="AMB_4", city_graph=graph, current_node="A", destination="E")

    state = ambulance.get_state()
    assert state["id"] == "AMB_4"
    assert state["agent_id"] == "AMB:4"
    assert state["current_node"] == "A"
    assert state["destination"] == "E"
    assert isinstance(state["planned_path"], list)
    assert isinstance(state["reservation_window"], dict)
    assert isinstance(state["arrived"], bool)
