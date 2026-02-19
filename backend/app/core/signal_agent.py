from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["N", "S", "E", "W"]


@dataclass(slots=True)
class SignalSnapshot:
    intersection_id: str
    current_phase: str
    phase_timer: int
    queue_state: dict[Direction, int]
    active_reservation: dict | None
    reservation_queue: list[dict]
    neighbor_ids: list[str]


@dataclass(slots=True)
class SignalAgent:
    agent_id: str
    intersection_id: str
    reservation_timeout: int
    priority_hysteresis_margin: float
    min_reservation_hold_ticks: int
    phase_duration: dict[str, int]
    neighbor_ids: list[str] = field(default_factory=list)
    phase_order: tuple[str, ...] = ("NS_GREEN", "NS_YELLOW", "EW_GREEN", "EW_YELLOW")
    current_phase: str = "NS_GREEN"
    phase_timer: int = 0
    queue_state: dict[Direction, int] = field(
        default_factory=lambda: {"N": 0, "S": 0, "E": 0, "W": 0}
    )
    active_reservation: dict | None = None
    reservation_queue: list[dict] = field(default_factory=list)
    _inbox: list[dict] = field(default_factory=list)
    _outbox: list[dict] = field(default_factory=list)

    def receive_message(self, message: dict) -> None:
        self._inbox.append(message)

    def tick(self, timestamp: int) -> None:
        self._process_messages(timestamp)
        self._expire_reservations(timestamp)
        self._maybe_activate_best(timestamp)
        self._update_phase(timestamp)

    def set_queue(self, direction: Direction, queue_length: int) -> None:
        self.queue_state[direction] = max(0, int(queue_length))

    def drain_outbox(self) -> list[dict]:
        out = list(self._outbox)
        self._outbox.clear()
        return out

    def get_snapshot(self) -> dict:
        snapshot = SignalSnapshot(
            intersection_id=self.intersection_id,
            current_phase=self.current_phase,
            phase_timer=self.phase_timer,
            queue_state=dict(self.queue_state),
            active_reservation=self._reservation_to_dict(self.active_reservation) if self.active_reservation else None,
            reservation_queue=[self._reservation_to_dict(item) for item in self.reservation_queue],
            neighbor_ids=list(self.neighbor_ids),
        )
        return {
            "intersection_id": snapshot.intersection_id,
            "current_phase": snapshot.current_phase,
            "phase_timer": snapshot.phase_timer,
            "queue_state": snapshot.queue_state,
            "active_reservation": snapshot.active_reservation,
            "reservation_queue": snapshot.reservation_queue,
            "neighbor_ids": snapshot.neighbor_ids,
        }

    def _process_messages(self, timestamp: int) -> None:
        while self._inbox:
            message = self._inbox.pop(0)
            msg_type = message.get("type")

            if msg_type == "reservation_request":
                self._handle_reservation_request(message, timestamp)
            elif msg_type == "reservation_release":
                corridor_id = str(message.get("payload", {}).get("corridor_id", ""))
                self._handle_reservation_release(corridor_id, timestamp)

    def _handle_reservation_request(self, message: dict, timestamp: int) -> None:
        payload = message.get("payload", {})
        ambulance_id = str(payload.get("ambulance_id", message.get("sender_id", "")))
        corridor_id = str(payload.get("corridor_id", f"{self.intersection_id}:{ambulance_id}"))
        priority = float(payload.get("priority", 0.0))
        required_phase = str(payload.get("required_phase", "NS_GREEN"))
        sender_id = str(message.get("sender_id", ""))

        entry = {
            "corridor_id": corridor_id,
            "ambulance_id": ambulance_id,
            "intersection_id": self.intersection_id,
            "sender_id": sender_id,
            "priority": priority,
            "required_phase": required_phase,
            "requested_at": timestamp,
            "activated_at": None,
            "expires_at": timestamp + self.reservation_timeout,
        }

        self._upsert_queue_entry(entry)
        self._sort_queue()
        self._maybe_activate_best(timestamp)

        approved = self.active_reservation is not None and self.active_reservation.get("corridor_id") == corridor_id
        reason = "approved" if approved else "queued"
        self._emit_response(target_id=sender_id, approved=approved, corridor_id=corridor_id, priority=priority, reason=reason, timestamp=timestamp)

    def _handle_reservation_release(self, corridor_id: str, timestamp: int) -> None:
        if self.active_reservation and self.active_reservation.get("corridor_id") == corridor_id:
            self.active_reservation = None

        self.reservation_queue = [item for item in self.reservation_queue if item.get("corridor_id") != corridor_id]
        self._maybe_activate_best(timestamp)

    def _expire_reservations(self, timestamp: int) -> None:
        if self.active_reservation and int(self.active_reservation.get("expires_at", 0)) <= timestamp:
            self.active_reservation = None

        self.reservation_queue = [
            item for item in self.reservation_queue if int(item.get("expires_at", 0)) > timestamp
        ]

    def _maybe_activate_best(self, timestamp: int) -> None:
        self._sort_queue()
        if self.active_reservation is None:
            self._activate_from_queue(timestamp)
            return

        if not self.reservation_queue:
            return

        challenger = self.reservation_queue[0]
        current_priority = float(self.active_reservation.get("priority", 0.0))
        challenger_priority = float(challenger.get("priority", 0.0))
        activated_raw = self.active_reservation.get("activated_at")
        activated_at = timestamp if activated_raw is None else int(activated_raw)

        hold_elapsed = timestamp - activated_at
        if hold_elapsed < self.min_reservation_hold_ticks:
            return

        if challenger_priority > current_priority + self.priority_hysteresis_margin:
            displaced = self.active_reservation
            self._send_revoke(displaced, timestamp)
            self.reservation_queue.append(displaced)
            self.active_reservation = None
            self._sort_queue()
            self._activate_from_queue(timestamp)

    def _activate_from_queue(self, timestamp: int) -> None:
        if not self.reservation_queue:
            return
        next_entry = self.reservation_queue.pop(0)
        next_entry["activated_at"] = timestamp
        self.active_reservation = next_entry
        self._emit_response(
            target_id=str(next_entry.get("sender_id", "")),
            approved=True,
            corridor_id=str(next_entry.get("corridor_id", "")),
            priority=float(next_entry.get("priority", 0.0)),
            reason="activated",
            timestamp=timestamp,
        )

    @staticmethod
    def _reservation_to_dict(reservation: dict) -> dict:
        if reservation is None:
            return {}
        return {
            "corridor_id": reservation.get("corridor_id"),
            "ambulance_id": reservation.get("ambulance_id"),
            "intersection_id": reservation.get("intersection_id"),
            "priority": reservation.get("priority"),
            "required_phase": reservation.get("required_phase"),
            "requested_at": reservation.get("requested_at"),
            "activated_at": reservation.get("activated_at"),
            "expires_at": reservation.get("expires_at"),
        }

    def _emit_response(
        self,
        target_id: str,
        approved: bool,
        corridor_id: str,
        priority: float,
        reason: str,
        timestamp: int,
    ) -> None:
        self._outbox.append(
            {
                "type": "reservation_response",
                "sender_id": self.agent_id,
                "target_id": target_id,
                "payload": {
                    "approved": approved,
                    "corridor_id": corridor_id,
                    "intersection_id": self.intersection_id,
                    "priority": priority,
                    "reason": reason,
                },
                "timestamp": timestamp,
            }
        )

    def _send_revoke(self, reservation: dict, timestamp: int) -> None:
        self._outbox.append(
            {
                "type": "reservation_revoke",
                "sender_id": self.agent_id,
                "target_id": reservation.get("sender_id"),
                "payload": {
                    "corridor_id": reservation.get("corridor_id"),
                    "intersection_id": self.intersection_id,
                    "reason": "displaced",
                },
                "timestamp": timestamp,
            }
        )

    def _upsert_queue_entry(self, entry: dict) -> None:
        corridor_id = str(entry.get("corridor_id", ""))
        if self.active_reservation and self.active_reservation.get("corridor_id") == corridor_id:
            active_since = self.active_reservation.get("activated_at")
            self.active_reservation.update(entry)
            self.active_reservation["activated_at"] = active_since
            return

        for idx, queued in enumerate(self.reservation_queue):
            if queued.get("corridor_id") == corridor_id:
                self.reservation_queue[idx] = entry
                return
        self.reservation_queue.append(entry)

    def _sort_queue(self) -> None:
        self.reservation_queue.sort(
            key=lambda item: (
                -float(item.get("priority", 0.0)),
                int(item.get("requested_at", 0)),
                str(item.get("corridor_id", "")),
            )
        )

    def _update_phase(self, timestamp: int) -> None:
        required_phase = None
        if self.active_reservation is not None:
            required_phase = str(self.active_reservation.get("required_phase", "NS_GREEN"))

        self.phase_timer += 1

        if required_phase is not None:
            if self.current_phase.endswith("GREEN") and self.current_phase != required_phase:
                self.current_phase = "NS_YELLOW" if self.current_phase == "NS_GREEN" else "EW_YELLOW"
                self.phase_timer = 0
                return

            if self.current_phase.endswith("YELLOW"):
                yellow_duration = self.phase_duration.get(self.current_phase, 5)
                if self.phase_timer >= yellow_duration:
                    self.current_phase = required_phase
                    self.phase_timer = 0
                return

            if self.current_phase == required_phase:
                activated_raw = self.active_reservation.get("activated_at")
                activated_at = timestamp if activated_raw is None else int(activated_raw)
                if timestamp - activated_at < self.min_reservation_hold_ticks:
                    return

        duration = self.phase_duration.get(self.current_phase, 30)
        if self.phase_timer >= duration:
            self._advance_phase()

    def _advance_phase(self) -> None:
        try:
            idx = self.phase_order.index(self.current_phase)
        except ValueError:
            idx = 0

        next_idx = (idx + 1) % len(self.phase_order)
        self.current_phase = self.phase_order[next_idx]
        self.phase_timer = 0
