from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from backend.app.api.app import app


def test_get_state_returns_200() -> None:
    with TestClient(app) as client:
        response = client.get("/state")
        assert response.status_code == 200
        body = response.json()
        assert isinstance(body, dict)
        assert "timestamp" in body


def test_spawn_ambulance_modifies_snapshot() -> None:
    with TestClient(app) as client:
        before = client.post("/reset", json={"seed": 77}).json()
        before_count = len(before.get("ambulances", []))
        nodes = [node["id"] for node in before.get("nodes", [])]
        start_node = nodes[0]
        destination_node = nodes[-1]

        response = client.post(
            "/spawn_ambulance",
            json={"start_node": start_node, "destination_node": destination_node},
        )
        assert response.status_code == 200

        after = client.get("/state").json()
        after_count = len(after.get("ambulances", []))
        assert after_count == before_count + 1


def test_reset_same_seed_produces_identical_state_twice() -> None:
    with TestClient(app) as client:
        state_1 = client.post("/reset", json={"seed": 1234}).json()
        state_2 = client.post("/reset", json={"seed": 1234}).json()

        assert state_1 == state_2


def test_reset_with_config_changes_grid_size() -> None:
    with TestClient(app) as client:
        snapshot = client.post(
            "/reset_with_config",
            json={"seed": 42, "grid_rows": 3, "grid_cols": 5, "tick_interval": 0.01},
        ).json()
        assert len(snapshot["nodes"]) == 15


def test_websocket_receives_snapshots() -> None:
    with TestClient(app) as client:
        client.post(
            "/reset_with_config",
            json={"seed": 99, "tick_interval": 0.01, "snapshot_broadcast_interval": 1},
        )
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()
            assert isinstance(message, dict)
            assert "timestamp" in message
            assert "metrics" in message


def test_concurrent_reset_does_not_crash() -> None:
    with TestClient(app) as client:
        def call_reset(seed: int) -> tuple[int, dict]:
            response = client.post("/reset", json={"seed": seed})
            return response.status_code, response.json()

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = [executor.submit(call_reset, seed) for seed in (1, 2, 3, 4, 5, 6)]

        results = [future.result() for future in futures]
        assert all(status == 200 for status, _ in results)
        assert all("timestamp" in body for _, body in results)


def test_chaos_spawn_is_deterministic_for_same_seed() -> None:
    with TestClient(app) as client:
        client.post("/reset", json={"seed": 10})
        first = client.post("/chaos", json={"count": 8, "seed": 123}).json()

        client.post("/reset", json={"seed": 10})
        second = client.post("/chaos", json={"count": 8, "seed": 123}).json()

        assert first["spawned"] == second["spawned"]
        assert first["ambulance_ids"] == second["ambulance_ids"]


def test_chaos_caps_to_node_minus_one() -> None:
    with TestClient(app) as client:
        snapshot = client.post("/reset_with_config", json={"seed": 22, "grid_rows": 3, "grid_cols": 3}).json()
        node_count = len(snapshot["nodes"])

        response = client.post("/chaos", json={"count": 999, "seed": 456})
        assert response.status_code == 400

        response_ok = client.post("/chaos", json={"count": 50, "seed": 456})
        assert response_ok.status_code == 200
        payload = response_ok.json()
        assert payload["spawned"] == node_count - 1
