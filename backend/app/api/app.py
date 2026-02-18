



from __future__ import annotations

import asyncio
import copy
import logging
import threading
import time

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.config import SNAPSHOT_BROADCAST_INTERVAL, TICK_INTERVAL
from backend.app.core.simulation_engine import SimulationEngine, SimulationEngineConfig

logger = logging.getLogger(__name__)

app = FastAPI(title="MARG API")

engine = SimulationEngine(config=SimulationEngineConfig(tick_interval=TICK_INTERVAL))
simulation_thread: threading.Thread | None = None
engine_lock = threading.Lock()
connected_clients: set[WebSocket] = set()
running = False
broadcaster_task: asyncio.Task | None = None


DEFAULT_ROADS: tuple[tuple[str, str], ...] = (
    ("A", "B"),
    ("B", "C"),
    ("C", "D"),
    ("D", "E"),
)


def _initialize_default_topology() -> None:
    for source, target in DEFAULT_ROADS:
        try:
            engine.add_road(source, target, base_time=1)
        except ValueError:
            pass
        if target not in engine.signals:
            engine.add_signal(target)


def simulation_loop() -> None:
    global running
    while running:
        try:
            with engine_lock:
                engine.step()
        except Exception as exc:
            logger.exception("Simulation loop error: %s", exc)
        time.sleep(TICK_INTERVAL)


async def _broadcast_loop() -> None:
    global running
    last_broadcast_tick = -1

    while running:
        await asyncio.sleep(max(TICK_INTERVAL / 2, 0.01))

        with engine_lock:
            tick = engine.tick_count
            if tick == last_broadcast_tick:
                continue
            if SNAPSHOT_BROADCAST_INTERVAL > 1 and tick % SNAPSHOT_BROADCAST_INTERVAL != 0:
                continue
            snapshot = copy.deepcopy(engine.get_system_snapshot())
            last_broadcast_tick = tick

        stale: list[WebSocket] = []
        for websocket in list(connected_clients):
            try:
                await websocket.send_json(snapshot)
            except Exception:
                stale.append(websocket)

        for websocket in stale:
            connected_clients.discard(websocket)
            try:
                await websocket.close()
            except Exception:
                pass


@app.on_event("startup")
async def on_startup() -> None:
    global running, simulation_thread, broadcaster_task

    with engine_lock:
        _initialize_default_topology()

    running = True
    simulation_thread = threading.Thread(target=simulation_loop, daemon=True, name="marg-simulation-thread")
    simulation_thread.start()
    broadcaster_task = asyncio.create_task(_broadcast_loop())


@app.on_event("shutdown")
async def on_shutdown() -> None:
    global running, simulation_thread, broadcaster_task

    running = False

    if simulation_thread is not None and simulation_thread.is_alive():
        simulation_thread.join(timeout=2)
    simulation_thread = None

    if broadcaster_task is not None:
        broadcaster_task.cancel()
        try:
            await broadcaster_task
        except asyncio.CancelledError:
            pass
        broadcaster_task = None


class SpawnRequest(BaseModel):
    start_node: str
    destination_node: str


class ResetRequest(BaseModel):
    seed: int


@app.get("/state")
def get_state() -> dict:
    with engine_lock:
        return copy.deepcopy(engine.get_system_snapshot())


@app.get("/metrics")
def get_metrics() -> dict:
    with engine_lock:
        return copy.deepcopy(engine.metrics_engine.export_snapshot())


@app.post("/spawn_ambulance")
def spawn_ambulance(payload: SpawnRequest) -> dict:
    with engine_lock:
        ambulance_id = engine.spawn_ambulance(payload.start_node, payload.destination_node)
    return {"status": "ok", "ambulance_id": ambulance_id}


@app.post("/reset")
def reset_simulation(payload: ResetRequest) -> dict:
    with engine_lock:
        engine.reset(seed=payload.seed)
        _initialize_default_topology()
        snapshot = copy.deepcopy(engine.get_system_snapshot())
    return {"status": "ok", "seed": payload.seed, "snapshot": snapshot}


@app.websocket("/ws")
async def websocket_stream(websocket: WebSocket) -> None:
    await websocket.accept()
    connected_clients.add(websocket)

    try:
        while running:
            try:
                await asyncio.wait_for(websocket.receive_text(), timeout=1.0)
            except TimeoutError:
                continue
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)
