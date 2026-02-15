from __future__ import annotations

import heapq
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass(slots=True)
class Edge:
    id: str
    source: str
    target: str
    base_time: float
    congestion_factor: float = 1.0
    capacity: float = 1.0

    @property
    def weight(self) -> float:
        return self.base_time * self.congestion_factor


class CityGraph:
    def __init__(self) -> None:
        self._nodes: set[str] = set()
        self._edges: Dict[str, Edge] = {}
        self._adj: Dict[str, List[Tuple[str, str]]] = {}

    def add_node(self, node_id: str) -> None:
        self._nodes.add(node_id)
        self._adj.setdefault(node_id, [])

    def add_edge(
        self,
        source: str,
        target: str,
        base_time: float,
        congestion_factor: float = 1.0,
        capacity: float = 1.0,
        edge_id: str | None = None,
    ) -> str:
        self.add_node(source)
        self.add_node(target)

        generated_id = edge_id or f"{source}_{target}"
        if generated_id in self._edges:
            raise ValueError(f"Edge with id '{generated_id}' already exists")

        edge = Edge(
            id=generated_id,
            source=source,
            target=target,
            base_time=float(base_time),
            congestion_factor=float(congestion_factor),
            capacity=float(capacity),
        )
        self._edges[generated_id] = edge
        self._adj[source].append((target, generated_id))
        return generated_id

    def get_intersections(self) -> list[dict]:
        return [{"id": node_id} for node_id in sorted(self._nodes)]

    def get_edges(self) -> list[dict]:
        return [
            {
                "id": edge.id,
                "source": edge.source,
                "target": edge.target,
                "base_time": edge.base_time,
                "congestion_factor": edge.congestion_factor,
                "capacity": edge.capacity,
            }
            for edge in self._edges.values()
        ]

    def get_edge_congestion(self, edge_id: str) -> float:
        edge = self._require_edge(edge_id)
        return edge.congestion_factor

    def set_edge_congestion(self, edge_id: str, congestion_factor: float) -> None:
        edge = self._require_edge(edge_id)
        edge.congestion_factor = max(0.01, float(congestion_factor))

    def shortest_path(self, source: str, target: str) -> tuple[list[str], float]:
        if source not in self._nodes:
            raise ValueError(f"Unknown source node: {source}")
        if target not in self._nodes:
            raise ValueError(f"Unknown target node: {target}")

        distances: Dict[str, float] = {node: float("inf") for node in self._nodes}
        previous: Dict[str, str | None] = {node: None for node in self._nodes}

        distances[source] = 0.0
        pq: list[tuple[float, str]] = [(0.0, source)]

        while pq:
            current_distance, node = heapq.heappop(pq)
            if current_distance > distances[node]:
                continue
            if node == target:
                break

            for neighbor, edge_id in self._adj.get(node, []):
                edge_weight = self._edges[edge_id].weight
                new_distance = current_distance + edge_weight
                if new_distance < distances[neighbor]:
                    distances[neighbor] = new_distance
                    previous[neighbor] = node
                    heapq.heappush(pq, (new_distance, neighbor))

        if distances[target] == float("inf"):
            return [], float("inf")

        path = self._reconstruct_path(previous=previous, source=source, target=target)
        return path, distances[target]

    def _reconstruct_path(self, previous: Dict[str, str | None], source: str, target: str) -> list[str]:
        path: list[str] = []
        current: str | None = target

        while current is not None:
            path.append(current)
            current = previous[current]

        path.reverse()
        if not path or path[0] != source:
            return []
        return path

    def _require_edge(self, edge_id: str) -> Edge:
        edge = self._edges.get(edge_id)
        if edge is None:
            raise ValueError(f"Unknown edge id: {edge_id}")
        return edge
