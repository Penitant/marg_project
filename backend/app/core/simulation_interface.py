from abc import ABC, abstractmethod
from typing import Any


class SimulationInterface(ABC):
    @abstractmethod
    def reset(self, seed: int) -> None:
        pass

    @abstractmethod
    def register_agent(self, agent: Any) -> None:
        pass

    @abstractmethod
    def deliver_message(self, message: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def step(self) -> None:
        pass
