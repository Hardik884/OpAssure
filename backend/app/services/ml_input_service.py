"""The unified AI/ML input payload (handover §16): one call, no DB queries on the ML side.

    {operator, machine, task, recentTelemetry, weather, history, asOf}

`asOf` is the point in (simulated) time the payload describes. Default: the time of
the machine's latest live telemetry row for this task (while replay runs), else
the task's start_time. Nothing after `asOf` is included, so the ML layer cannot
see the future. Top-level keys follow the handover; nested fields are DB names.
"""

from datetime import datetime

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError, NotFoundError
from app.models import Machine, Operator, Task, Telemetry, Weather
from app.schemas.core import MachineOut, OperatorOut, TaskOut
from app.services import task_service, telemetry_service
from app.services.weather_service import WeatherService, weather_service

RECENT_TELEMETRY_ROWS = 30


def _task_history(db: Session, operator_id: str, before: datetime) -> list[dict]:
    """Operator's completed tasks before `before`, oldest first, with telemetry aggregates + start weather."""
    tasks = db.scalars(select(Task).where(Task.operator_id == operator_id, Task.status == "completed",
                                          Task.start_time < before).order_by(Task.start_time)).all()
    if not tasks:
        return []
    ids = [t.task_id for t in tasks]
    agg = {r.task_id: r for r in db.execute(
        select(Telemetry.task_id,
               func.avg(Telemetry.avg_cycle_time_s).label("avg_cycle_time_s"),
               func.sum(Telemetry.fuel_used_l).label("fuel_used_l"),
               func.sum(Telemetry.load_cycles).label("load_cycles"),
               func.sum(case((Telemetry.idle_reason == "avoidable", Telemetry.idling_time_min), else_=0)).label("avoidable_idle_min"),
               func.sum(case((Telemetry.idle_reason == "truck_wait", Telemetry.idling_time_min), else_=0)).label("truck_wait_idle_min"),
               func.sum(Telemetry.harsh_events).label("harsh_events"),
               func.sum(case((Telemetry.safety_alert == "seatbelt", 1), else_=0)).label("seatbelt_alerts"))
        .where(Telemetry.task_id.in_(ids)).group_by(Telemetry.task_id))}
    hours = {t.start_time.replace(minute=0, second=0, microsecond=0) for t in tasks}
    weather = {w.timestamp: w for w in db.scalars(select(Weather).where(Weather.timestamp.in_(hours)))}

    out = []
    for t in tasks:
        a = agg.get(t.task_id)
        w = weather.get(t.start_time.replace(minute=0, second=0, microsecond=0))
        out.append({
            **TaskOut.model_validate(t).model_dump(),
            "avg_cycle_time_s": round(a.avg_cycle_time_s, 2) if a and a.avg_cycle_time_s is not None else None,
            "fuel_used_l": round(a.fuel_used_l, 2) if a else None,
            "load_cycles": int(a.load_cycles) if a else None,
            "avoidable_idle_min": float(a.avoidable_idle_min) if a else None,
            "truck_wait_idle_min": float(a.truck_wait_idle_min) if a else None,
            "harsh_events": int(a.harsh_events) if a else None,
            "seatbelt_alerts": int(a.seatbelt_alerts) if a else None,
            "temperature": w.temperature if w else None,
            "rain_mm": w.rain_mm if w else None,
            "wind_speed": w.wind_speed if w else None,
        })
    return out


def build_ml_input(db: Session, operator_id: str, task_id: str | None = None, as_of: datetime | None = None,
                   store: telemetry_service.LiveTelemetryStore = telemetry_service.live_store,
                   weather: WeatherService = weather_service) -> dict:
    operator = db.get(Operator, operator_id)
    if operator is None:
        raise NotFoundError("operator", operator_id)
    today = task_service.get_today(db)
    if task_id:
        task = db.get(Task, task_id)
        if task is None:
            raise NotFoundError("task", task_id)
        if task.operator_id != operator_id:
            raise InvalidRequestError(f"Task {task_id} belongs to {task.operator_id}, not {operator_id}")
    else:
        task = task_service.current_task(db, operator_id, today)
        if task is None:
            raise NotFoundError("task", f"(any task for {operator_id})")
    machine = db.get(Machine, task.machine_id)

    if as_of is None:
        live = store.latest(task.machine_id)
        as_of = live["timestamp"] if live and live.get("task_id") == task.task_id else task.start_time

    recent = db.scalars(select(Telemetry).where(Telemetry.operator_id == operator_id, Telemetry.timestamp <= as_of)
                        .order_by(Telemetry.timestamp.desc(), Telemetry.id.desc()).limit(RECENT_TELEMETRY_ROWS)).all()
    day_start, _ = task_service.day_bounds(today)
    return {
        "operator": OperatorOut.model_validate(operator).model_dump(),
        "machine": MachineOut.model_validate(machine).model_dump(),
        "task": TaskOut.model_validate(task).model_dump(),
        "recentTelemetry": [telemetry_service.telemetry_to_dict(r) for r in reversed(recent)],
        "weather": weather.get_weather(db, as_of),
        "history": _task_history(db, operator_id, min(day_start, as_of)),
        "asOf": as_of,
    }
