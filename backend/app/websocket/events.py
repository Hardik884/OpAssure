"""WebSocket event payloads (handover §11). Builders only — transport comes with replay.

Every message is an envelope with a stable `type` and a payload `version`:

    {"type": "telemetry_update", "version": 1, "payload": {...}}

Payload keys follow the handover contract (camelCase), plus machineId/operatorId/
taskId so a client can route the event.
"""

from datetime import datetime

from app.services.safety_service import SafetyAlert

EVENT_VERSION = 1
EVENT_TYPES = ("telemetry_update", "safety_alert", "proximity_alert", "eta_update",
               "habit_detected", "training_recommendation")


def _iso(value):
    return value.isoformat() if isinstance(value, datetime) else value


def envelope(event_type: str, payload: dict) -> dict:
    if event_type not in EVENT_TYPES:
        raise ValueError(f"Unknown event type {event_type!r}")
    return {"type": event_type, "version": EVENT_VERSION, "payload": {k: _iso(v) for k, v in payload.items()}}


def telemetry_update(row: dict) -> dict:
    return envelope("telemetry_update", {
        "machineId": row["machine_id"], "operatorId": row["operator_id"], "taskId": row["task_id"],
        "timestamp": row["timestamp"], "cycleTime": row["avg_cycle_time_s"], "idle": row["idling_time_min"],
        "fuel": row["fuel_used_l"], "belt": row["seatbelt_status"], "movement": row["machine_moving"],
    })


def safety_alert(alert: SafetyAlert, row: dict) -> dict:
    return envelope("safety_alert", {
        "machineId": row["machine_id"], "operatorId": row["operator_id"], "taskId": row["task_id"],
        "timestamp": row["timestamp"], "severity": alert.severity, "type": alert.type, "message": alert.message,
    })


def proximity_alert(machine_id: str, timestamp, severity: str, distance_m: float, direction: str,
                    worker_id: str | None = None) -> dict:
    return envelope("proximity_alert", {
        "machineId": machine_id, "timestamp": timestamp, "workerId": worker_id,
        "severity": severity, "distance": round(distance_m, 1), "direction": direction,
    })


def eta_update(task_id: str, eta_min: float, eta_max: float, original: float, reason: str,
               buckets_remaining: int) -> dict:
    return envelope("eta_update", {"taskId": task_id, "min": eta_min, "max": eta_max, "original": original,
                                   "reason": reason, "bucketsRemaining": buckets_remaining})


def habit_detected(operator_id: str, habit: dict) -> dict:
    """`habit` is an item from insights_service.detect_habits()."""
    return envelope("habit_detected", {"operatorId": operator_id, "habitType": habit["habit_type"],
                                       "count": habit["count"], "explanation": habit["explanation"]})


def training_recommendation(operator_id: str, rec: dict) -> dict:
    """`rec` is an item from training_service.recommendations()["recommendations"]."""
    return envelope("training_recommendation", {"operatorId": operator_id, "clipId": rec["clip_id"],
                                                "title": rec["title"], "reason": rec["reason"]})
