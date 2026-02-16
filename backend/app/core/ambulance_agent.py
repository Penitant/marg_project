from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.core.city_graph import CityGraph


@dataclass(slots=True)
class AmbulanceAgent:
    ambulance_id: str
    city_graph: CityGraph
    source: str
    destination: str
    current_node: str = field(init=False)
    path: list[str] = field(default_factory=list)
    travel_time: float = 0.0
    eta: float = float("inf")
    arrived: bool = False

    def __post_init__(self) -> None:
        self.current_node = self.source
        self.recompute_route()

    def recompute_route(self) -> None:
        path, distance = self.city_graph.shortest_path(self.current_node, self.destination)
        self.path = path
        self.eta = distance

        if self.current_node == self.destination:
            self.arrived = True
            self.eta = 0.0

    def step(self) -> None:
        if self.arrived:
            return

        self.recompute_route()
        if len(self.path) < 2:
            if self.current_node == self.destination:
                self.arrived = True
                self.eta = 0.0
            return

        next_node = self.path[1]
        edge_weight = self._edge_weight(self.current_node, next_node)

        self.current_node = next_node
        self.travel_time += edge_weight

        if self.current_node == self.destination:
            self.arrived = True
            self.eta = 0.0
        else:
            self.recompute_route()

    def get_state(self) -> dict:
        return {
            "id": self.ambulance_id,
            "current_node": self.current_node,
            "destination": self.destination,
            "path": list(self.path),
            "eta": self.eta,
            "travel_time": self.travel_time,
            "arrived": self.arrived,
        }

    def _edge_weight(self, source: str, target: str) -> float:
        for edge in self.city_graph.get_edges():
            if edge.get("source") == source and edge.get("target") == target:
                return float(edge.get("base_time", 0.0)) * float(edge.get("congestion_factor", 1.0))
        raise ValueError(f"No edge found from {source} to {target}")
