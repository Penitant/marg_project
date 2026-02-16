from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence


@dataclass(frozen=True, slots=True)
class AmbulancePriorityInput:
    ambulance_id: str
    remaining_distance: float
    severity_score: float | None = None
    arrival_order: int | None = None


@dataclass(frozen=True, slots=True)
class ArbitrationDecision:
    winner_id: str | None
    ranked_ids: tuple[str, ...]


def rank_ambulances(candidates: Sequence[AmbulancePriorityInput]) -> tuple[AmbulancePriorityInput, ...]:
    """
    Rank ambulances by:
    1) shortest remaining distance,
    2) highest severity score,
    3) FIFO via arrival_order,
    4) stable ambulance_id tie-breaker.
    """
    return tuple(sorted(candidates, key=_priority_key))


def choose_preemption_winner(candidates: Sequence[AmbulancePriorityInput]) -> ArbitrationDecision:
    ranked = rank_ambulances(candidates)
    if not ranked:
        return ArbitrationDecision(winner_id=None, ranked_ids=())

    return ArbitrationDecision(
        winner_id=ranked[0].ambulance_id,
        ranked_ids=tuple(item.ambulance_id for item in ranked),
    )


def filter_conflicting_candidates(
    candidates: Iterable[AmbulancePriorityInput],
    allowed_ids: set[str],
) -> tuple[AmbulancePriorityInput, ...]:
    """
    Return only candidates that are part of the current conflict set.
    """
    return tuple(candidate for candidate in candidates if candidate.ambulance_id in allowed_ids)


def _priority_key(item: AmbulancePriorityInput) -> tuple[float, float, int, str]:
    remaining_distance = max(0.0, float(item.remaining_distance))

    severity = item.severity_score if item.severity_score is not None else 0.0
    severity_key = -float(severity)

    arrival_order = item.arrival_order if item.arrival_order is not None else 10**12

    return (remaining_distance, severity_key, int(arrival_order), item.ambulance_id)
