# MARG Phase 6 Protocol Contract

## 1. Ambulance Agent Contract

- Corridor behavior: the ambulance maintains a sliding reservation window of depth `MAX_CORRIDOR_LENGTH` over upcoming intersections in `planned_path`.
- Movement gating: movement to the next intersection is allowed only when every intersection in the current window has reservation state `approved`.
- Priority definition:

  ```
  effective_priority = base_priority + WAIT_ALPHA * waiting_ticks
  ```

  where `base_priority` is computed from route geometry and current congestion, and `waiting_ticks` is derived from first request time.
- Aging monotonicity: `waiting_ticks` is non-negative and non-decreasing while waiting for reservation progress.
- Aging reset: `first_reservation_request_timestamp` and `waiting_ticks` reset when the ambulance advances to the next intersection.
- Revocation handling: on `reservation_revoke`, the ambulance releases all held reservations and marks reservation state as denied/cooldown transition.
- Cooldown semantics: during `REVOCATION_COOLDOWN_TICKS`, the ambulance continues ticking and ETA updates but must not emit new reservation requests.
- Replan trigger: route recomputation occurs only after denial/revocation retry count reaches `MAX_RETRY_BEFORE_REPLAN`.
- Determinism: for fixed seed and identical initial state, emitted message order, reservation requests, and movement outcomes are deterministic.

## 2. Signal Agent Contract

- Single active invariant: each signal has at most one `active_reservation`.
- Queue ordering: `reservation_queue` ordering is deterministic by descending priority, ascending request timestamp, and lexicographic corridor identifier tie-break.
- Displacement rule: active reservation displacement is allowed only when:
  - hold duration is at least `MIN_RESERVATION_HOLD_TICKS`, and
  - challenger priority exceeds active priority by `PRIORITY_HYSTERESIS_MARGIN`.
- Revocation locality: displacement emits revoke only for the local signal’s current active reservation; no global cascade is allowed.
- Scope boundary: signal decisions are local and must not depend on global routing state or centralized policy.

## 3. Deadlock Resolution Contract

- Wait-for graph construction:
  - vertices: ambulance identifiers involved in active/queued reservations,
  - edges: waiter ambulance → holder ambulance per intersection.
- Detection algorithm: SCC detection via Tarjan-style strongly connected components.
- Deadlock criterion: SCC size > 1.
- Hold-aware filtering: intersections with active reservations younger than `MIN_RESERVATION_HOLD_TICKS` are excluded from deadlock candidate graph.
- Victim minimality: exactly one revocation victim per detected SCC.
- Deterministic victim rule: for each SCC, victim is ambulance with largest `requested_at`; tie broken by lexicographically highest ambulance id.
- Engine role boundary: engine may detect SCCs and emit revoke messages; engine must not compute route choices or reservation priorities.

## 4. System Invariants

- At any tick, no intersection has more than one active reservation.
- For each signal, an ambulance id cannot appear in both `active_reservation` and `reservation_queue` simultaneously.
- Each signal queue contains no duplicate ambulance entries.
- Ambulance `waiting_ticks` is never negative.
- Snapshot and metric state are JSON-serializable.
- Replay determinism: with identical seed and scenario initialization, snapshots, metrics, and revocation ordering are identical.