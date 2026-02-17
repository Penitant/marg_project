import pytest

from backend.app.core.simulation_interface import SimulationInterface


def test_simulation_interface_is_abstract() -> None:
    with pytest.raises(TypeError):
        SimulationInterface()


def test_concrete_subclass_can_be_instantiated_when_methods_are_implemented() -> None:
    class ConcreteSimulation(SimulationInterface):
        def reset(self, seed: int) -> None:
            return None

        def register_agent(self, agent: object) -> None:
            return None

        def deliver_message(self, message: dict) -> None:
            return None

        def step(self) -> None:
            return None

    simulation = ConcreteSimulation()
    simulation.step()
