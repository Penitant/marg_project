from datetime import datetime

import pytest

from backend.app.core.traffic_generator import TrafficGenerator, TrafficGeneratorConfig


class FakeCityGraph:
    def __init__(self) -> None:
        self.edges = [
            {"id": "A_B", "congestion_factor": 1.0},
            {"id": "B_C", "congestion_factor": 1.5},
            {"id": None, "congestion_factor": 2.0},
        ]
        self.updates: list[tuple[str, float]] = []

    def get_edges(self) -> list[dict]:
        return self.edges

    def set_edge_congestion(self, edge_id: str, congestion_factor: float) -> None:
        self.updates.append((edge_id, congestion_factor))


def test_update_modifies_only_edges_with_valid_ids() -> None:
    fake_graph = FakeCityGraph()
    cfg = TrafficGeneratorConfig(random_min=1.0, random_max=1.0)
    generator = TrafficGenerator(fake_graph, cfg)

    generator.update(datetime(2026, 2, 15, 12, 0))

    assert len(fake_graph.updates) == 2
    updated_ids = {edge_id for edge_id, _ in fake_graph.updates}
    assert updated_ids == {"A_B", "B_C"}


def test_peak_hour_multiplier_applies() -> None:
    fake_graph = FakeCityGraph()
    cfg = TrafficGeneratorConfig(peak_multiplier=1.4, random_min=1.0, random_max=1.0)
    generator = TrafficGenerator(fake_graph, cfg)

    generator.update(datetime(2026, 2, 15, 8, 30))

    updates = dict(fake_graph.updates)
    assert updates["A_B"] == 1.4
    assert updates["B_C"] == pytest.approx(2.1)


def test_force_rush_hour_overrides_time_of_day() -> None:
    fake_graph = FakeCityGraph()
    cfg = TrafficGeneratorConfig(peak_multiplier=1.5, random_min=1.0, random_max=1.0)
    generator = TrafficGenerator(fake_graph, cfg)
    generator.set_force_rush_hour(True)

    generator.update(datetime(2026, 2, 15, 3, 0))

    updates = dict(fake_graph.updates)
    assert updates["A_B"] == 1.5
    assert updates["B_C"] == 2.25


def test_congestion_values_are_clamped_to_config_bounds() -> None:
    fake_graph = FakeCityGraph()
    cfg = TrafficGeneratorConfig(
        peak_multiplier=10.0,
        random_min=1.0,
        random_max=1.0,
        min_congestion=0.5,
        max_congestion=2.0,
    )
    generator = TrafficGenerator(fake_graph, cfg)

    generator.update(datetime(2026, 2, 15, 8, 0))

    for _, congestion in fake_graph.updates:
        assert 0.5 <= congestion <= 2.0
