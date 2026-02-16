from backend.app.core.ambulance_agent import AmbulanceAgent
from backend.app.core.city_graph import CityGraph


def _build_simple_graph() -> CityGraph:
    graph = CityGraph()
    graph.add_edge("A", "B", base_time=2, congestion_factor=1.0)
    graph.add_edge("B", "C", base_time=3, congestion_factor=1.0)
    return graph


def test_ambulance_initial_route_and_eta() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent("AMB_1", graph, source="A", destination="C")

    assert ambulance.current_node == "A"
    assert ambulance.path == ["A", "B", "C"]
    assert ambulance.eta == 5.0
    assert ambulance.arrived is False


def test_step_moves_one_hop_and_accumulates_travel_time() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent("AMB_2", graph, source="A", destination="C")

    ambulance.step()
    assert ambulance.current_node == "B"
    assert ambulance.travel_time == 2.0
    assert ambulance.arrived is False

    ambulance.step()
    assert ambulance.current_node == "C"
    assert ambulance.travel_time == 5.0
    assert ambulance.arrived is True
    assert ambulance.eta == 0.0


def test_get_state_returns_json_serializable_shape() -> None:
    graph = _build_simple_graph()
    ambulance = AmbulanceAgent("AMB_3", graph, source="A", destination="C")

    state = ambulance.get_state()
    assert state["id"] == "AMB_3"
    assert state["current_node"] == "A"
    assert state["destination"] == "C"
    assert isinstance(state["path"], list)
    assert isinstance(state["arrived"], bool)
