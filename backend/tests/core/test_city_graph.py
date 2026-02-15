from backend.app.core.city_graph import CityGraph


def test_add_edge_and_get_edges_contains_expected_fields() -> None:
    graph = CityGraph()
    edge_id = graph.add_edge("A", "B", base_time=5, congestion_factor=1.2, capacity=10)

    edges = graph.get_edges()
    assert len(edges) == 1
    assert edges[0]["id"] == edge_id
    assert edges[0]["source"] == "A"
    assert edges[0]["target"] == "B"
    assert edges[0]["base_time"] == 5.0
    assert edges[0]["congestion_factor"] == 1.2
    assert edges[0]["capacity"] == 10.0


def test_shortest_path_uses_dynamic_weight() -> None:
    graph = CityGraph()
    graph.add_edge("A", "B", base_time=1, congestion_factor=1.0)
    graph.add_edge("B", "C", base_time=1, congestion_factor=1.0)
    graph.add_edge("A", "C", base_time=3, congestion_factor=1.0)

    path, distance = graph.shortest_path("A", "C")
    assert path == ["A", "B", "C"]
    assert distance == 2.0

    graph.set_edge_congestion("A_B", 4.0)
    path, distance = graph.shortest_path("A", "C")
    assert path == ["A", "C"]
    assert distance == 3.0


def test_set_edge_congestion_is_clamped_to_positive_minimum() -> None:
    graph = CityGraph()
    graph.add_edge("X", "Y", base_time=5)
    graph.set_edge_congestion("X_Y", 0)

    assert graph.get_edge_congestion("X_Y") == 0.01


def test_shortest_path_unknown_nodes_raise_value_error() -> None:
    graph = CityGraph()
    graph.add_node("A")

    try:
        graph.shortest_path("A", "Z")
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "Unknown target node" in str(exc)
