from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Direction = Literal["N", "S", "E", "W"]


@dataclass(slots=True)
class SignalSnapshot:
    intersection_id: str
    current_phase: str
    phase_timer: int
    queue_by_direction: dict[Direction, int]
    emergency_override: bool
    override_direction: Direction | None


@dataclass(slots=True)
class SignalAgent:
    intersection_id: str
    phase_order: tuple[str, ...] = ("NS_GREEN", "NS_YELLOW", "EW_GREEN", "EW_YELLOW")
    phase_duration: dict[str, int] = field(
        default_factory=lambda: {
            "NS_GREEN": 30,
            "NS_YELLOW": 5,
            "EW_GREEN": 30,
            "EW_YELLOW": 5,
        }
    )
    current_phase: str = "NS_GREEN"
    phase_timer: int = 0
    queue_by_direction: dict[Direction, int] = field(
        default_factory=lambda: {"N": 0, "S": 0, "E": 0, "W": 0}
    )
    emergency_override: bool = False
    override_direction: Direction | None = None

    def update_phase(self) -> None:
        if self.emergency_override:
            return

        self.phase_timer += 1
        duration = self.phase_duration.get(self.current_phase, 30)
        if self.phase_timer >= duration:
            self._advance_phase()

    def trigger_preemption(self, direction: Direction) -> None:
        self.emergency_override = True
        self.override_direction = direction
        self.current_phase = self._phase_for_direction(direction)
        self.phase_timer = 0

    def release_preemption(self) -> None:
        self.emergency_override = False
        self.override_direction = None
        if self.current_phase.endswith("YELLOW"):
            self.current_phase = "NS_GREEN"
        self.phase_timer = 0

    def set_queue(self, direction: Direction, queue_length: int) -> None:
        self.queue_by_direction[direction] = max(0, int(queue_length))

    def get_snapshot(self) -> dict:
        snapshot = SignalSnapshot(
            intersection_id=self.intersection_id,
            current_phase=self.current_phase,
            phase_timer=self.phase_timer,
            queue_by_direction=dict(self.queue_by_direction),
            emergency_override=self.emergency_override,
            override_direction=self.override_direction,
        )
        return {
            "intersection_id": snapshot.intersection_id,
            "current_phase": snapshot.current_phase,
            "phase_timer": snapshot.phase_timer,
            "queue_by_direction": snapshot.queue_by_direction,
            "emergency_override": snapshot.emergency_override,
            "override_direction": snapshot.override_direction,
        }

    def _advance_phase(self) -> None:
        try:
            idx = self.phase_order.index(self.current_phase)
        except ValueError:
            idx = 0

        next_idx = (idx + 1) % len(self.phase_order)
        self.current_phase = self.phase_order[next_idx]
        self.phase_timer = 0

    def _phase_for_direction(self, direction: Direction) -> str:
        if direction in ("N", "S"):
            return "NS_GREEN"
        return "EW_GREEN"
