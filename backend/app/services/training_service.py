"""Training recommendations (from detected habits + assigned training) and completion."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.errors import InvalidRequestError
from app.models import Operator, Telemetry, TrainingEvent
from app.services.insights_service import operator_habits

# trigger (= habit_type) -> clip. metric_name matches the habit's metric.
CATALOG = {
    "seatbelt": {"clip_id": "CLIP_SEATBELT_01", "title": "Buckle up before you move",
                 "metric_name": "seatbelt_violations", "priority": "high"},
    "avoidable_idle": {"clip_id": "CLIP_IDLE_01", "title": "Cutting avoidable idle",
                       "metric_name": "avoidable_idle_min_per_hour", "priority": "medium"},
    "harsh_events": {"clip_id": "CLIP_SMOOTH_01", "title": "Smooth swings and braking",
                     "metric_name": "harsh_events_per_hour", "priority": "medium"},
    "afternoon_slowdown": {"clip_id": "CLIP_FATIGUE_01", "title": "Managing afternoon fatigue",
                           "metric_name": "afternoon_pace_ratio", "priority": "medium"},
    "fuel_inefficiency": {"clip_id": "CLIP_FUEL_01", "title": "Fuel-efficient digging",
                          "metric_name": "fuel_vs_fleet_ratio", "priority": "medium"},
}
CLIP_TO_TRIGGER = {v["clip_id"]: k for k, v in CATALOG.items()}
_PRIORITY_ORDER = {"high": 0, "medium": 1}


def recommendations(db: Session, operator: Operator, before: datetime) -> dict:
    metrics, fleet, habits = operator_habits(db, operator, before)
    events = db.scalars(select(TrainingEvent).where(TrainingEvent.operator_id == operator.operator_id)
                        .order_by(TrainingEvent.timestamp)).all()
    completed_triggers = {e.trigger for e in events if e.completed}
    assigned = {e.trigger: e for e in events if not e.completed}

    recs = []
    for habit in habits:
        trigger = habit["habit_type"]
        if trigger in completed_triggers:
            continue
        clip = CATALOG[trigger]
        recs.append({"clip_id": clip["clip_id"], "title": clip["title"], "trigger": trigger,
                     "reason": habit["explanation"], "priority": clip["priority"],
                     "status": "assigned" if trigger in assigned else "recommended",
                     "metric_name": clip["metric_name"], "current_metric": habit["metric"],
                     "fleet_metric": habit["fleet_metric"]})
    for trigger, event in assigned.items():  # assigned earlier, habit no longer above threshold
        if trigger in CATALOG and all(r["trigger"] != trigger for r in recs):
            clip = CATALOG[trigger]
            recs.append({"clip_id": event.clip_id, "title": clip["title"], "trigger": trigger,
                         "reason": "Assigned training not yet completed.", "priority": clip["priority"],
                         "status": "assigned", "metric_name": event.metric_name,
                         "current_metric": metrics.get(event.metric_name), "fleet_metric": fleet.get(event.metric_name)})
    recs.sort(key=lambda r: _PRIORITY_ORDER[r["priority"]])
    return {"operator_id": operator.operator_id, "recommendations": recs,
            "completed": [e for e in events if e.completed]}


def complete(db: Session, operator: Operator, clip_id: str, before: datetime, timestamp: datetime | None,
             before_metric: float | None, after_metric: float | None) -> tuple[TrainingEvent, bool]:
    trigger = CLIP_TO_TRIGGER.get(clip_id)
    if trigger is None:
        raise InvalidRequestError(f"Unknown clip_id {clip_id!r}. Known clips: {', '.join(sorted(CLIP_TO_TRIGGER))}")
    metric_name = CATALOG[trigger]["metric_name"]
    if timestamp is None:
        timestamp = db.scalar(select(Telemetry.timestamp).where(Telemetry.operator_id == operator.operator_id)
                              .order_by(Telemetry.timestamp.desc()).limit(1)) or datetime.now()

    event = db.scalars(select(TrainingEvent).where(
        TrainingEvent.operator_id == operator.operator_id, TrainingEvent.clip_id == clip_id,
        TrainingEvent.completed.is_(False)).order_by(TrainingEvent.timestamp).limit(1)).first()
    created = event is None
    if created:
        event = TrainingEvent(operator_id=operator.operator_id, trigger=trigger, clip_id=clip_id,
                              metric_name=metric_name)
        db.add(event)
    event.completed = True
    event.timestamp = timestamp
    event.after_metric = after_metric
    # before_metric: explicit value > value stored when assigned > operator's current metric.
    if before_metric is not None:
        event.before_metric = before_metric
    elif event.before_metric is None:
        metrics, _, _ = operator_habits(db, operator, before)
        event.before_metric = metrics.get(metric_name)
    db.commit()
    db.refresh(event)
    return event, created
