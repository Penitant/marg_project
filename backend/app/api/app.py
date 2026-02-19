



from __future__ import annotations

import asyncio
import copy
import logging
import threading
import time
from dataclasses import asdict

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from backend.config import EngineConfig
from backend.app.core.simulation_engine import SimulationEngine

logger = logging.getLogger(__name__)

app = FastAPI(title="MARG API")

engine = SimulationEngine(config=EngineConfig())
simulation_thread: threading.Thread | None = None
engine_lock = threading.Lock()
connected_clients: set[WebSocket] = set()
running = False
broadcaster_task: asyncio.Task | None = None


def simulation_loop() -> None:
    global running
    while running:
        try:
            with engine_lock:
                engine.step()
                tick_interval = engine.config.tick_interval
        except Exception as exc:
            logger.exception("Simulation loop error: %s", exc)
            tick_interval = 0.01
        time.sleep(max(float(tick_interval), 0.0))


async def _broadcast_loop() -> None:
    global running

    while running:
        with engine_lock:
            broadcast_interval = max(float(engine.config.snapshot_broadcast_interval), 0.01)
        await asyncio.sleep(broadcast_interval)

        with engine_lock:
            snapshot = copy.deepcopy(engine.get_system_snapshot())

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


class ResetWithConfigRequest(BaseModel):
    seed: int
    grid_rows: int | None = None
    grid_cols: int | None = None
    tick_interval: float | None = None
    corridor_depth: int | None = None
    reservation_timeout: int | None = None
    deadlock_check_interval: int | None = None
    revocation_cooldown_ticks: int | None = None
    wait_alpha: float | None = None
    priority_hysteresis_margin: float | None = None
    default_phase_duration: int | None = None
    yellow_phase_duration: int | None = None
    min_reservation_hold_ticks: int | None = None
    max_retry_before_replan: int | None = None
    alpha: float | None = None
    beta: float | None = None
    congestion_jitter: float | None = None
    min_congestion_factor: float | None = None
    peak_multiplier: float | None = None
    snapshot_broadcast_interval: int | None = None


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
    return {"ambulance_id": ambulance_id}


@app.post("/reset")
def reset_simulation(payload: ResetRequest) -> dict:
    with engine_lock:
        engine.reset(seed=payload.seed)
        snapshot = copy.deepcopy(engine.get_system_snapshot())
    return snapshot


@app.post("/reset_with_config")
def reset_with_config(payload: ResetWithConfigRequest) -> dict:
    global engine

    overrides = payload.model_dump(exclude_none=True)
    seed = int(overrides.pop("seed"))
    merged = asdict(EngineConfig())
    merged.update(overrides)
    new_config = EngineConfig(**merged)

    with engine_lock:
        replacement = SimulationEngine(config=new_config)
        replacement.reset(seed=seed)
        engine = replacement
        snapshot = copy.deepcopy(engine.get_system_snapshot())

    return snapshot


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
