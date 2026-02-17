from __future__ import annotations

from dataclasses import dataclass, field

from backend.app.core.city_graph import CityGraph

CORRIDOR_DEPTH = 3
ALPHA = 0.7
BETA = 0.3
MAX_RETRY_BEFORE_REPLAN = 3


@dataclass(slots=True)
class AmbulanceAgent:
    agent_id: str
    ambulance_id: str
    city_graph: CityGraph
    current_node: str
    destination: str
    planned_path: list[str] = field(default_factory=list)
    path_index: int = 0
    corridor_depth: int = CORRIDOR_DEPTH
    alpha: float = ALPHA
    beta: float = BETA
    max_retry_before_replan: int = MAX_RETRY_BEFORE_REPLAN
    reservation_status: str = "idle"
    response_time: float = 0.0
    eta: float = field(default=float("inf"), init=False)
    arrived: bool = False
    retry_counter: int = 0
    reservation_window: dict[str, dict] = field(default_factory=dict)
    _inbox: list[dict] = field(default_factory=list)
    _outbox: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.compute_path()

    def compute_path(self) -> None:
        path, distance = self.city_graph.shortest_path(self.current_node, self.destination)
        self.planned_path = path
        self.eta = distance
        self.path_index = 0
        self.retry_counter = 0
        self.reservation_window.clear()

        if self.current_node == self.destination:
            self.arrived = True
            self.eta = 0.0

    def receive_message(self, message: dict) -> None:
        self._inbox.append(message)

    def tick(self, timestamp: int) -> None:
        self._process_messages()
        if self.arrived:
            return

        if len(self.planned_path) < 2:
            if self.current_node == self.destination:
                self.arrived = True
                self.eta = 0.0
            return

        self._sync_path_index()
        window = self._next_window_nodes()
        if not window:
            self.arrived = self.current_node == self.destination
            if self.arrived:
                self.eta = 0.0
            return

        self._request_window_reservations(window, timestamp)

        if not self._window_fully_approved(window):
            self.reservation_status = "pending"
            return

        next_node = window[0]

        edge_weight = self._edge_weight(self.current_node, next_node)
        prev_node = self.current_node
        self.current_node = next_node
        self.path_index += 1
        self.response_time += edge_weight
        self._update_remaining_eta()

        if self.current_node == self.destination:
            self.arrived = True
            self.eta = 0.0
            self._release_all_reservations(timestamp)
            return

        self._release_reservation_for_junction(prev_node, next_node, timestamp)
        self._prune_past_reservations()
        self.reservation_status = "idle"

    def drain_outbox(self) -> list[dict]:
        out = list(self._outbox)
        self._outbox.clear()
        return out

    def get_state(self) -> dict:
        return {
            "id": self.ambulance_id,
            "agent_id": self.agent_id,
            "current_node": self.current_node,
            "destination": self.destination,
            "planned_path": list(self.planned_path),
            "path_index": self.path_index,
            "eta": self.eta,
            "response_time": self.response_time,
            "reservation_status": self.reservation_status,
            "reservation_window": {k: dict(v) for k, v in self.reservation_window.items()},
            "retry_counter": self.retry_counter,
            "arrived": self.arrived,
        }

    def _process_messages(self) -> None:
        while self._inbox:
            message = self._inbox.pop(0)
            if message.get("type") != "reservation_response":
                if message.get("type") == "reservation_revoke":
                    self._handle_reservation_revoke(message)
                continue
            self._handle_reservation_response(message)

    def _handle_reservation_response(self, message: dict) -> None:
        payload = message.get("payload", {})
        junction_id = str(payload.get("intersection_id", ""))
        if not junction_id:
            return

        approved = bool(payload.get("approved", False))
        corridor_id = str(payload.get("corridor_id", f"{self.ambulance_id}:{junction_id}"))
        priority = float(payload.get("priority", 0.0))
        state = self.reservation_window.get(junction_id, {})

        if approved:
            state.update(
                {
                    "status": "approved",
                    "corridor_id": corridor_id,
                    "priority": priority,
                    "retry_count": int(state.get("retry_count", 0)),
                }
            )
            self.reservation_window[junction_id] = state
            self.reservation_status = "approved"
            return

        retry_count = int(state.get("retry_count", 0)) + 1
        state.update(
            {
                "status": "denied",
                "corridor_id": corridor_id,
                "priority": priority,
                "retry_count": retry_count,
            }
        )
        self.reservation_window[junction_id] = state
        self.retry_counter += 1
        self.reservation_status = "denied"

        if self.retry_counter >= self.max_retry_before_replan:
            self.compute_path()

    def _handle_reservation_revoke(self, message: dict) -> None:
        payload = message.get("payload", {})
        junction_id = str(payload.get("intersection_id", ""))
        if not junction_id:
            return

        state = self.reservation_window.get(junction_id, {})
        state.update(
            {
                "status": "revoked",
                "retry_count": int(state.get("retry_count", 0)) + 1,
                "corridor_id": payload.get("corridor_id"),
            }
        )
        self.reservation_window[junction_id] = state
        self.reservation_status = "denied"

    def _request_window_reservations(self, window: list[str], timestamp: int) -> None:
        for junction_id in window:
            state = self.reservation_window.get(junction_id, {})
            if state.get("status") == "approved":
                continue

            retry_count = int(state.get("retry_count", 0))
            if retry_count >= self.max_retry_before_replan:
                continue

            target_idx = self.planned_path.index(junction_id)
            priority = self.compute_priority(target_idx)
            required_phase = self._required_phase_for_index(target_idx)
            corridor_id = str(state.get("corridor_id", f"{self.ambulance_id}:{junction_id}"))

            self._outbox.append(
                {
                    "type": "reservation_request",
                    "sender_id": self.agent_id,
                    "target_id": f"SIG:{junction_id}",
                    "payload": {
                        "ambulance_id": self.ambulance_id,
                        "corridor_id": corridor_id,
                        "intersection_id": junction_id,
                        "priority": priority,
                        "required_phase": required_phase,
                        "distance_to_junction": self._distance_to_path_index(target_idx),
                        "remaining_distance": self._remaining_distance_from_current(),
                    },
                    "timestamp": timestamp,
                }
            )
            self.reservation_window[junction_id] = {
                "status": "pending",
                "corridor_id": corridor_id,
                "priority": priority,
                "retry_count": retry_count,
            }

    def _release_reservation_for_junction(self, previous_node: str, junction_id: str, timestamp: int) -> None:
        state = self.reservation_window.get(junction_id)
        if not state:
            return

        corridor_id = str(state.get("corridor_id", f"{self.ambulance_id}:{junction_id}"))
        self._outbox.append(
            {
                "type": "reservation_release",
                "sender_id": self.agent_id,
                "target_id": f"SIG:{junction_id}",
                "payload": {
                    "ambulance_id": self.ambulance_id,
                    "corridor_id": corridor_id,
                    "intersection_id": junction_id,
                    "previous_node": previous_node,
                },
                "timestamp": timestamp,
            }
        )
        self.reservation_window.pop(junction_id, None)

    def _release_all_reservations(self, timestamp: int) -> None:
        for junction_id, state in list(self.reservation_window.items()):
            corridor_id = str(state.get("corridor_id", f"{self.ambulance_id}:{junction_id}"))
            self._outbox.append(
                {
                    "type": "reservation_release",
                    "sender_id": self.agent_id,
                    "target_id": f"SIG:{junction_id}",
                    "payload": {
                        "ambulance_id": self.ambulance_id,
                        "corridor_id": corridor_id,
                        "intersection_id": junction_id,
                    },
                    "timestamp": timestamp,
                }
            )
        self.reservation_window.clear()

    def _next_window_nodes(self) -> list[str]:
        start = self.path_index + 1
        end = start + self.corridor_depth
        return self.planned_path[start:end]

    def _window_fully_approved(self, window: list[str]) -> bool:
        for junction_id in window:
            if self.reservation_window.get(junction_id, {}).get("status") != "approved":
                return False
        return True

    def _prune_past_reservations(self) -> None:
        valid = set(self._next_window_nodes())
        for junction_id in list(self.reservation_window.keys()):
            if junction_id not in valid:
                self.reservation_window.pop(junction_id, None)

    def compute_priority(self, target_path_index: int) -> float:
        remaining_distance = max(self._remaining_distance_from_current(), 0.0001)
        distance_to_junction = max(self._distance_to_path_index(target_path_index), 0.0001)
        return (self.alpha * (1.0 / remaining_distance)) + (self.beta * (1.0 / distance_to_junction))

    def _remaining_distance_from_current(self) -> float:
        total = 0.0
        idx = self.path_index
        while idx < len(self.planned_path) - 1:
            total += self._edge_weight(self.planned_path[idx], self.planned_path[idx + 1])
            idx += 1
        return total

    def _distance_to_path_index(self, target_idx: int) -> float:
        if target_idx <= self.path_index:
            return 0.0
        total = 0.0
        idx = self.path_index
        while idx < target_idx:
            total += self._edge_weight(self.planned_path[idx], self.planned_path[idx + 1])
            idx += 1
        return total

    def _required_phase_for_index(self, target_idx: int) -> str:
        if target_idx <= 0:
            return "NS_GREEN"
        source = self.planned_path[target_idx - 1]
        target = self.planned_path[target_idx]
        return "NS_GREEN" if str(source) <= str(target) else "EW_GREEN"

    def _sync_path_index(self) -> None:
        try:
            self.path_index = self.planned_path.index(self.current_node)
        except ValueError:
            self.path_index = 0

    def _update_remaining_eta(self) -> None:
        self.eta = self._remaining_distance_from_current()

    def _edge_weight(self, source: str, target: str) -> float:
        for edge in self.city_graph.get_edges():
            if edge.get("source") == source and edge.get("target") == target:
                return float(edge.get("base_time", 0.0)) * float(edge.get("congestion_factor", 1.0))
        raise ValueError(f"No edge found from {source} to {target}")
