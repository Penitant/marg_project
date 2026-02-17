from __future__ import annotations

from dataclasses import dataclass, field
from heapq import heappop, heappush
from itertools import count
from typing import Protocol


class MessageReceiver(Protocol):
    agent_id: str

    def receive_message(self, message: dict) -> None:
        pass


@dataclass(slots=True)
class MessageBus:
    _queue: list[tuple[int, int, dict]] = field(default_factory=list)
    _sequence: count = field(default_factory=count)

    def publish(self, message: dict) -> None:
        timestamp = int(message.get("timestamp", 0))
        heappush(self._queue, (timestamp, next(self._sequence), message))

    def process(self, receivers: dict[str, MessageReceiver]) -> int:
        delivered = 0
        while self._queue:
            _, _, message = heappop(self._queue)
            target_id = message.get("target_id")
            if target_id is None:
                continue
            receiver = receivers.get(str(target_id))
            if receiver is None:
                continue
            receiver.receive_message(message)
            delivered += 1
        return delivered

    def clear(self) -> None:
        self._queue.clear()

    def size(self) -> int:
        return len(self._queue)
