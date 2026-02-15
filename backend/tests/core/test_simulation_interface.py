import pytest

from backend.app.core.simulation_interface import SimulationInterface


def test_simulation_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        SimulationInterface()


def test_concrete_subclass_can_be_instantiated_when_methods_are_implemented() -> None:
    class ConcreteSimulation(SimulationInterface):
        def get_intersections(self) -> list[dict]:
            return []

        def get_edges(self) -> list[dict]:
            return []

        def get_edge_congestion(self, edge_id: str) -> float:
            return 1.0

        def set_signal_state(self, intersection_id: str, state: dict) -> None:
            return None

        def spawn_ambulance(self, source: str, destination: str) -> str:
            return "AMB_1"

        def get_ambulance_state(self, ambulance_id: str) -> dict:
            return {"id": ambulance_id}

        def step(self) -> None:
            return None

    simulation = ConcreteSimulation()
    assert simulation.get_intersections() == []
