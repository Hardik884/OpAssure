"""Incident creation with the Black Box telemetry snapshot (handover §15).

Snapshot source, in order:
  live_buffer  rows from the last ~60 s of live telemetry for the machine (replay/ingest)
  database     otherwise the machine's last 5 stored rows up to the incident time
  none         the machine has no telemetry
"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError, NotFoundError
from app.models import Incident, Machine, Operator, Task
from app.schemas.events import IncidentCreate
from app.services import telemetry_service


def create_incident(db: Session, payload: IncidentCreate,
                    store: telemetry_service.LiveTelemetryStore = telemetry_service.live_store) -> dict:
    operator_id, machine_id = payload.operator_id, payload.machine_id
    if payload.task_id:
        task = db.get(Task, payload.task_id)
        if task is None:
            raise NotFoundError("task", payload.task_id)
        for field, given, actual in (("operator_id", operator_id, task.operator_id),
                                     ("machine_id", machine_id, task.machine_id)):
            if given and given != actual:
                raise InvalidRequestError(f"{field} {given} does not match task {task.task_id} ({actual})")
        operator_id, machine_id = task.operator_id, task.machine_id
    if not operator_id or not machine_id:
        raise InvalidRequestError("Provide task_id, or both operator_id and machine_id")
    if db.get(Operator, operator_id) is None:
        raise NotFoundError("operator", operator_id)
    if db.get(Machine, machine_id) is None:
        raise NotFoundError("machine", machine_id)

    live_rows = store.snapshot(machine_id)
    latest, _ = telemetry_service.get_latest(db, machine_id, store)
    timestamp = payload.timestamp or (latest["timestamp"] if latest else datetime.now())
    task_id = payload.task_id
    if task_id is None and latest and latest["operator_id"] == operator_id:
        task_id = latest["task_id"]  # link to the task the operator is running on this machine

    if live_rows:
        rows, source = live_rows, "live_buffer"
    else:
        rows = telemetry_service.recent_rows(db, machine_id, timestamp)
        source = "database" if rows else "none"

    incident = Incident(
        timestamp=timestamp, machine_id=machine_id, operator_id=operator_id, task_id=task_id,
        type=payload.type, severity=payload.severity, description=payload.description,
        telemetry_snapshot=[telemetry_service.to_jsonable(r) for r in rows], source="operator",
    )
    db.add(incident)
    db.commit()
    db.refresh(incident)
    return {**{c: getattr(incident, c) for c in (
        "id", "timestamp", "machine_id", "operator_id", "task_id", "type", "severity", "description", "source",
        "telemetry_snapshot")}, "snapshot_source": source, "snapshot_size": len(rows)}


def incidents_for_operator(db: Session, operator_id: str) -> list[Incident]:
    return list(db.scalars(select(Incident).where(Incident.operator_id == operator_id)
                           .order_by(Incident.timestamp.desc(), Incident.id.desc())))
