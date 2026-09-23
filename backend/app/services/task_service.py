"""Task lookups and the definition of "today".

The dataset is historical (2025), so "today" is the demo day: DEMO_DATE if set,
otherwise the latest task date in the database (the seeded demo day, 2025-06-29).
"""

import logging
from datetime import date, datetime, time, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import get_demo_date
from app.models import Task

logger = logging.getLogger("opassure.tasks")


def get_today(db: Session) -> date:
    configured = get_demo_date()
    if configured:
        try:
            return date.fromisoformat(configured)
        except ValueError:
            logger.warning("Ignoring invalid DEMO_DATE=%r (expected YYYY-MM-DD)", configured)
    latest = db.scalar(select(func.max(Task.start_time)))
    return latest.date() if latest else date.today()


def day_bounds(day: date) -> tuple[datetime, datetime]:
    start = datetime.combine(day, time(0, 0))
    return start, start + timedelta(days=1)


def tasks_for_day(db: Session, operator_id: str, day: date) -> list[Task]:
    start, end = day_bounds(day)
    return list(db.scalars(select(Task).where(Task.operator_id == operator_id, Task.start_time >= start,
                                              Task.start_time < end).order_by(Task.start_time)))


def current_task(db: Session, operator_id: str, day: date) -> Task | None:
    """First not-yet-completed task today; else the last task today; else the operator's latest task."""
    today = tasks_for_day(db, operator_id, day)
    pending = [t for t in today if t.status != "completed"]
    if pending:
        return pending[0]
    if today:
        return today[-1]
    return db.scalars(select(Task).where(Task.operator_id == operator_id)
                      .order_by(Task.start_time.desc()).limit(1)).first()
