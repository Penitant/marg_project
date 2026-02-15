from abc import ABC, abstractmethod
from typing import Any


class SimulationInterface(ABC):
    @abstractmethod
    def get_intersections(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def get_edges(self) -> list[dict[str, Any]]:
        pass

    @abstractmethod
    def get_edge_congestion(self, edge_id: str) -> float:
        pass

    @abstractmethod
    def set_signal_state(self, intersection_id: str, state: dict[str, Any]) -> None:
        pass

    @abstractmethod
    def spawn_ambulance(self, source: str, destination: str) -> str:
        pass

    @abstractmethod
    def get_ambulance_state(self, ambulance_id: str) -> dict[str, Any]:
        pass

    @abstractmethod
    def step(self) -> None:
        pass
