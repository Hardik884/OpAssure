"""Judge Control Panel — for live demos. Anyone in the room can trigger a real
event (a worker intrusion, a rainstorm, a cycle-time spike) and watch ETA, risk
and safety alerts update across the app within one WebSocket round trip.

Every injected event is computed by the SAME rule engine / ETA function real
telemetry uses (safety_service.evaluate_proximity, eta_service.estimate_eta via
ReplayProcessor) — nothing here fabricates an output number, it only feeds a
synthetic-but-plausible input through the real pipeline. Requires the T001
replay to already be running (POST /demo/start).
"""

from fastapi import APIRouter, HTTPException

from app.api.demo import replay_engine
from app.schemas.judge import CycleSpikeIn, ProximityInjectIn, RainInjectIn

router = APIRouter(prefix="/judge", tags=["judge"])


def _require_running() -> None:
    if not replay_engine.running:
        raise HTTPException(status_code=409, detail="Start the replay first: POST /demo/start")


@router.post("/proximity", summary="Trigger a worker-in-swing-zone intrusion")
async def proximity(payload: ProximityInjectIn):
    _require_running()
    events = await replay_engine.inject_proximity(payload.distance_m, payload.direction)
    return {"triggered": bool(events), "events": events}


@router.post("/rain", summary="Drop a rainstorm on the site (relabels the ETA reason + the correlated cycle-time hit)")
async def rain(payload: RainInjectIn):
    _require_running()
    events = await replay_engine.inject_rain(payload.rain_mm, payload.cycle_multiplier)
    return {"triggered": bool(events), "events": events}


@router.post("/cycle-spike", summary="Spike recent cycle time (a mechanical/operator slowdown, not weather)")
async def cycle_spike(payload: CycleSpikeIn):
    _require_running()
    events = await replay_engine.inject_cycle_spike(payload.multiplier)
    return {"triggered": bool(events), "events": events}


@router.post("/reset", summary="Clear every judge-triggered override (rain, cycle spike, proximity) without stopping the replay")
async def reset():
    _require_running()
    events = await replay_engine.clear_judge_overrides()
    return {"events": events}
