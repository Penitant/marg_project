from __future__ import annotations

import json
import math

from backend.config import EngineConfig
from backend.app.core.simulation_engine import SimulationEngine


def _edge_pairs(snapshot: dict) -> set[tuple[str, str]]:
    return {(edge["source"], edge["target"]) for edge in snapshot["edges"]}


def _collect_exact_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, dict):
        values: list[str] = []
        for item in value.values():
            values.extend(_collect_exact_strings(item))
        return values
    if isinstance(value, list):
        values: list[str] = []
        for item in value:
            values.extend(_collect_exact_strings(item))
        return values
    return []


def test_generate_3x3_grid_topology_is_deterministic() -> None:
    config = EngineConfig(grid_rows=3, grid_cols=3, tick_interval=0.0)
    engine = SimulationEngine(config=config)
    snapshot = engine.get_system_snapshot()

    assert len(snapshot["nodes"]) == 9
    assert len(snapshot["edges"]) == 24

    expected_nodes = [f"r{row}c{col}" for row in range(3) for col in range(3)]
    assert [item["id"] for item in snapshot["nodes"]] == expected_nodes

    expected_pairs: set[tuple[str, str]] = set()
    for row in range(3):
        for col in range(3):
            current = f"r{row}c{col}"
            if col + 1 < 3:
                right = f"r{row}c{col+1}"
                expected_pairs.add((current, right))
                expected_pairs.add((right, current))
            if row + 1 < 3:
                down = f"r{row+1}c{col}"
                expected_pairs.add((current, down))
                expected_pairs.add((down, current))

    assert _edge_pairs(snapshot) == expected_pairs


def test_config_variation_changes_topology_size() -> None:
    small = SimulationEngine(config=EngineConfig(grid_rows=2, grid_cols=4, tick_interval=0.0))
    large = SimulationEngine(config=EngineConfig(grid_rows=5, grid_cols=5, tick_interval=0.0))

    small_snapshot = small.get_system_snapshot()
    large_snapshot = large.get_system_snapshot()

    assert len(small_snapshot["nodes"]) == 8
    assert len(large_snapshot["nodes"]) == 25


def test_reset_same_seed_is_fully_deterministic() -> None:
    engine = SimulationEngine(config=EngineConfig(grid_rows=4, grid_cols=4, tick_interval=0.0))

    engine.reset(seed=123)
    state_1 = engine.get_system_snapshot()

    engine.reset(seed=123)
    state_2 = engine.get_system_snapshot()

    assert state_1 == state_2


def test_integration_stress_10x10_5_ambulances_2000_ticks() -> None:
    config = EngineConfig(grid_rows=10, grid_cols=10, tick_interval=0.0, deadlock_check_interval=1)
    engine = SimulationEngine(config=config)
    engine.reset(seed=2026)

    for index in range(5):
        engine.spawn_ambulance(source="r0c0", destination="r9c9", ambulance_id=f"AMB_{index+1}")

    engine.run_for_ticks(2000, sleep=False)
    snapshot = engine.get_system_snapshot()
    metrics = snapshot["metrics"]

    assert all(agent.arrived for agent in engine.ambulances.values())
    assert metrics["deadlock_scc_count"] >= 0
    assert math.isfinite(float(metrics["fairness_index"]))
    json.dumps(snapshot)


def test_snapshot_contains_no_legacy_hardcoded_nodes() -> None:
    engine = SimulationEngine(config=EngineConfig(grid_rows=3, grid_cols=3, tick_interval=0.0))
    snapshot = engine.get_system_snapshot()

    legacy_names = {"A", "B", "C", "D", "E"}
    all_exact_strings = _collect_exact_strings(snapshot)

    assert legacy_names.isdisjoint(all_exact_strings)
