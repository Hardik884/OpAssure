"""Shared router helpers."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.core.errors import NotFoundError
from app.services import task_service


def get_or_404(db: Session, model, resource_id: str, resource: str):
    obj = db.get(model, resource_id)
    if obj is None:
        raise NotFoundError(resource, resource_id)
    return obj


def history_cutoff(db: Session) -> datetime:
    """Start of "today": insights/recommendations only use data before this."""
    start, _ = task_service.day_bounds(task_service.get_today(db))
    return start
