from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ReservationClaim:
    ambulance_id: str
    corridor_id: str
    intersection_id: str
    priority: float
    requested_at: int


def should_displace(
    current_priority: float,
    challenger_priority: float,
    hysteresis_margin: float,
    active_since: int,
    timestamp: int,
    min_hold_ticks: int,
) -> bool:
    if timestamp - active_since < min_hold_ticks:
        return False
    return challenger_priority > current_priority + hysteresis_margin


def sort_claims_for_queue(claims: list[ReservationClaim]) -> list[ReservationClaim]:
    return sorted(
        claims,
        key=lambda claim: (-claim.priority, claim.requested_at, claim.ambulance_id),
    )


def build_wait_for_graph(
    active_by_intersection: dict[str, str],
    queued_by_intersection: dict[str, list[str]],
) -> dict[str, set[str]]:
    wait_for: dict[str, set[str]] = {}

    for intersection_id, holder in active_by_intersection.items():
        for waiter in queued_by_intersection.get(intersection_id, []):
            if waiter == holder:
                continue
            wait_for.setdefault(waiter, set()).add(holder)

    return wait_for


def detect_deadlock_cycles(wait_for: dict[str, set[str]]) -> list[tuple[str, ...]]:
    nodes = set(wait_for.keys())
    for neighbors in wait_for.values():
        nodes.update(neighbors)

    index = 0
    index_map: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    stack: list[str] = []
    on_stack: set[str] = set()
    sccs: list[tuple[str, ...]] = []

    for start in sorted(nodes):
        if start in index_map:
            continue

        frames: list[dict] = [
            {
                "node": start,
                "neighbors": iter(sorted(wait_for.get(start, set()))),
                "parent": None,
                "entered": False,
            }
        ]

        while frames:
            frame = frames[-1]
            node = str(frame["node"])

            if not frame["entered"]:
                frame["entered"] = True
                index_map[node] = index
                lowlink[node] = index
                index += 1
                stack.append(node)
                on_stack.add(node)

            try:
                neighbor = next(frame["neighbors"])
                if neighbor not in index_map:
                    frames.append(
                        {
                            "node": neighbor,
                            "neighbors": iter(sorted(wait_for.get(neighbor, set()))),
                            "parent": node,
                            "entered": False,
                        }
                    )
                elif neighbor in on_stack:
                    lowlink[node] = min(lowlink[node], index_map[neighbor])
            except StopIteration:
                frames.pop()
                parent = frame["parent"]
                if parent is not None:
                    lowlink[parent] = min(lowlink[parent], lowlink[node])

                if lowlink[node] == index_map[node]:
                    component: list[str] = []
                    while stack:
                        member = stack.pop()
                        on_stack.discard(member)
                        component.append(member)
                        if member == node:
                            break

                    if len(component) > 1:
                        sccs.append(tuple(sorted(component)))

    return sorted(sccs)


def select_revocations_for_cycles(
    cycles: list[tuple[str, ...]],
    requested_at_by_ambulance: dict[str, int],
) -> set[str]:
    victims: set[str] = set()

    for cycle in cycles:
        victim = max(
            cycle,
            key=lambda ambulance_id: (
                requested_at_by_ambulance.get(ambulance_id, 10**12),
                ambulance_id,
            ),
        )
        victims.add(victim)

    return victims
