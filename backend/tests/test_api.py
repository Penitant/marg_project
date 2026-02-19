from __future__ import annotations

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
        client.post("/reset", json={"seed": 77})
        before = client.get("/state").json()
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
        reset_1 = client.post("/reset", json={"seed": 1234})
        assert reset_1.status_code == 200
        state_1 = client.get("/state").json()

        reset_2 = client.post("/reset", json={"seed": 1234})
        assert reset_2.status_code == 200
        state_2 = client.get("/state").json()

        assert state_1 == state_2


def test_websocket_receives_snapshots() -> None:
    with TestClient(app) as client:
        with client.websocket_connect("/ws") as websocket:
            message = websocket.receive_json()
            assert isinstance(message, dict)
            assert "timestamp" in message
            assert "metrics" in message
