from backend.app.core.arbitration import (
    AmbulancePriorityInput,
    choose_preemption_winner,
    filter_conflicting_candidates,
    rank_ambulances,
)


def test_rank_ambulances_uses_distance_then_severity_then_fifo() -> None:
    candidates = [
        AmbulancePriorityInput("AMB_2", remaining_distance=10, severity_score=1, arrival_order=2),
        AmbulancePriorityInput("AMB_1", remaining_distance=10, severity_score=3, arrival_order=3),
        AmbulancePriorityInput("AMB_3", remaining_distance=8, severity_score=1, arrival_order=1),
    ]

    ranked = rank_ambulances(candidates)
    assert [item.ambulance_id for item in ranked] == ["AMB_3", "AMB_1", "AMB_2"]


def test_choose_preemption_winner_returns_none_for_empty_candidates() -> None:
    decision = choose_preemption_winner([])
    assert decision.winner_id is None
    assert decision.ranked_ids == ()


def test_filter_conflicting_candidates_selects_allowed_ids_only() -> None:
    candidates = [
        AmbulancePriorityInput("AMB_1", remaining_distance=5),
        AmbulancePriorityInput("AMB_2", remaining_distance=6),
    ]

    filtered = filter_conflicting_candidates(candidates, {"AMB_2"})
    assert [item.ambulance_id for item in filtered] == ["AMB_2"]
