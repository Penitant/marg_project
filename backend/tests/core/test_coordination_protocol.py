from backend.app.core.coordination_protocol import (
    ReservationClaim,
    build_wait_for_graph,
    detect_deadlock_cycles,
    select_revocations_for_cycles,
    should_displace,
    sort_claims_for_queue,
)


def test_should_displace_respects_hold_and_hysteresis() -> None:
    assert should_displace(
        current_priority=1.0,
        challenger_priority=1.2,
        hysteresis_margin=0.05,
        active_since=10,
        timestamp=11,
        min_hold_ticks=2,
    ) is False

    assert should_displace(
        current_priority=1.0,
        challenger_priority=1.03,
        hysteresis_margin=0.05,
        active_since=10,
        timestamp=13,
        min_hold_ticks=2,
    ) is False

    assert should_displace(
        current_priority=1.0,
        challenger_priority=1.2,
        hysteresis_margin=0.05,
        active_since=10,
        timestamp=13,
        min_hold_ticks=2,
    ) is True


def test_sort_claims_is_deterministic() -> None:
    claims = [
        ReservationClaim("AMB_2", "C2", "B", 1.0, 5),
        ReservationClaim("AMB_1", "C1", "B", 1.0, 5),
        ReservationClaim("AMB_3", "C3", "B", 2.0, 6),
    ]
    sorted_claims = sort_claims_for_queue(claims)
    assert [claim.ambulance_id for claim in sorted_claims] == ["AMB_3", "AMB_1", "AMB_2"]


def test_scc_detection_no_cycle_returns_empty() -> None:
    wait_for = {"A": {"B"}, "B": {"C"}, "C": set()}
    assert detect_deadlock_cycles(wait_for) == []


def test_scc_detection_single_two_node_cycle() -> None:
    wait_for = {"A": {"B"}, "B": {"A"}}
    assert detect_deadlock_cycles(wait_for) == [("A", "B")]


def test_scc_detection_three_node_cycle() -> None:
    wait_for = {"A": {"B"}, "B": {"C"}, "C": {"A"}}
    assert detect_deadlock_cycles(wait_for) == [("A", "B", "C")]


def test_scc_detection_two_independent_cycles() -> None:
    wait_for = {
        "A": {"B"},
        "B": {"A"},
        "C": {"D"},
        "D": {"C"},
        "E": set(),
    }
    assert detect_deadlock_cycles(wait_for) == [("A", "B"), ("C", "D")]


def test_scc_detection_large_acyclic_graph() -> None:
    wait_for = {f"A{i}": {f"A{i+1}"} for i in range(1, 25)}
    wait_for["A25"] = set()
    assert detect_deadlock_cycles(wait_for) == []


def test_deadlock_cycle_detection_and_deterministic_victim() -> None:
    active_by_intersection = {
        "I1": "AMB_A",
        "I2": "AMB_B",
    }
    queued_by_intersection = {
        "I1": ["AMB_B"],
        "I2": ["AMB_A"],
    }

    wait_for = build_wait_for_graph(active_by_intersection, queued_by_intersection)
    cycles = detect_deadlock_cycles(wait_for)

    assert cycles == [("AMB_A", "AMB_B")]

    victims = select_revocations_for_cycles(
        cycles,
        requested_at_by_ambulance={"AMB_A": 10, "AMB_B": 20},
    )
    assert victims == {"AMB_B"}


def test_minimal_revocation_one_per_scc_and_no_duplicates() -> None:
    cycles = [("AMB_1", "AMB_2"), ("AMB_2", "AMB_3", "AMB_4")]
    victims = select_revocations_for_cycles(
        cycles,
        requested_at_by_ambulance={"AMB_1": 1, "AMB_2": 2, "AMB_3": 3, "AMB_4": 3},
    )
    assert len(victims) == 2
    assert victims == {"AMB_2", "AMB_4"}
