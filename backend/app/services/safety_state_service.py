"""Current safety state of a machine: latest telemetry + nearest worker + the safety rules."""

from datetime import timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import WorkerPosition
from app.services import telemetry_service
from app.services.safety_service import (
    distance_and_bearing, evaluate_all, overall_status, proximity_severity, relative_direction,
)

# Worker positions are sampled every 10 min in the synthetic data; older fixes are stale.
WORKER_FIX_MAX_AGE = timedelta(minutes=10)


def nearest_worker(db: Session, lat: float, lon: float, at) -> dict | None:
    """Closest worker using each worker's latest fix in (at - 10 min, at]."""
    latest_ts = (select(WorkerPosition.worker_id, func.max(WorkerPosition.timestamp).label("ts"))
                 .where(WorkerPosition.timestamp <= at, WorkerPosition.timestamp > at - WORKER_FIX_MAX_AGE)
                 .group_by(WorkerPosition.worker_id).subquery())
    fixes = db.execute(select(WorkerPosition).join(
        latest_ts, (WorkerPosition.worker_id == latest_ts.c.worker_id) & (WorkerPosition.timestamp == latest_ts.c.ts)
    )).scalars().all()
    best = None
    for fix in fixes:
        dist, bearing = distance_and_bearing(lat, lon, fix.lat, fix.lon)
        if best is None or dist < best["distance_m"]:
            best = {"worker_id": fix.worker_id, "distance_m": round(dist, 1),
                    "direction": relative_direction(bearing), "zone": proximity_severity(dist),
                    "timestamp": fix.timestamp}
    return best


def safety_state(db: Session, machine_id: str, store=telemetry_service.live_store) -> dict | None:
    """None when the machine has no telemetry at all."""
    latest, source = telemetry_service.get_latest(db, machine_id, store)
    if latest is None:
        return None
    idle = store.idle_minutes(machine_id) if source == "live" else telemetry_service.idle_minutes_from_db(db, latest)
    worker = nearest_worker(db, latest["lat"], latest["lon"], latest["timestamp"])
    alerts = evaluate_all(
        seatbelt_status=latest["seatbelt_status"], machine_moving=latest["machine_moving"],
        idle_minutes=idle, idle_reason=latest["idle_reason"],
        worker_distance_m=worker["distance_m"] if worker else None,
        worker_direction=worker["direction"] if worker else None,
    )
    return {
        "machine_id": machine_id,
        "status": overall_status(alerts),
        "timestamp": latest["timestamp"],
        "operator_id": latest["operator_id"],
        "task_id": latest["task_id"],
        "seatbelt_status": latest["seatbelt_status"],
        "machine_moving": latest["machine_moving"],
        "idle_minutes": idle,
        "idle_reason": latest["idle_reason"],
        "nearest_worker": worker,
        "alerts": [a.to_dict() for a in alerts],
        "source": source,
    }
