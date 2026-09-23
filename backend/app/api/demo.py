"""Demo replay control: start / stop / reset / status of the T001 telemetry replay."""

from fastapi import APIRouter, Query

from app.services.replay_service import ReplayEngine
from app.websocket.manager import manager

router = APIRouter(tags=["demo"])

replay_engine = ReplayEngine(broadcast=manager.broadcast)


@router.post("/demo/start", summary="Start the T001 replay (no-op if already running)")
async def start(interval: float | None = Query(None, ge=0, le=60,
                                               description="Seconds between rows; default REPLAY_INTERVAL_SECONDS")):
    status, started = await replay_engine.start(interval)
    return {"started": started, "message": "Replay started" if started else "Replay already running",
            "status": status, "clients": manager.count}


@router.post("/demo/stop", summary="Stop the replay (live state is kept)")
async def stop():
    return {"status": await replay_engine.stop()}


@router.post("/demo/reset", summary="Stop the replay and clear EXC001 live state")
async def reset():
    return {"status": await replay_engine.reset()}


@router.get("/demo/status", summary="Replay status")
async def status():
    return {"status": replay_engine.status(), "clients": manager.count}
