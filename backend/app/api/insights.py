"""Unified ML intelligence — backed by the real `ml/` package (see
`app/services/ml_bridge.py` and `ml/docs/integration.md`), not a
deterministic fallback.

Operator/task lookups and error mapping follow the same pattern as the
other routers (`get_or_404`, `NotFoundError`/`InvalidRequestError`).
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.core.errors import InvalidRequestError, NotFoundError
from app.db.session import get_db
from app.models import Operator, Task
from app.services import ml_bridge, task_service

router = APIRouter(tags=["insights"])


@router.get(
    "/insights/operator/{operator_id}/ml",
    summary="Unified ML intelligence: Operator Twin, ETA, Habit Radar, Idle Shield, "
    "Focus Battery, risk, fuel diagnosis, training recommendation, threat briefing",
)
def ml_insights(
    operator_id: str,
    task_id: str | None = Query(None, description="Default: operator's current task today"),
    db: Session = Depends(get_db),
):
    operator = get_or_404(db, Operator, operator_id, "operator")

    if task_id:
        task = get_or_404(db, Task, task_id, "task")
        if task.operator_id != operator_id:
            raise InvalidRequestError(f"Task {task_id} belongs to {task.operator_id}, not {operator_id}")
    else:
        today = task_service.get_today(db)
        task = task_service.current_task(db, operator_id, today)
        if task is None:
            raise NotFoundError("task", f"(any task for {operator_id})")

    try:
        state = ml_bridge.get_operator_state(db, operator.operator_id, task.machine_id, task.task_id)
    except ml_bridge.MLNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise InvalidRequestError(str(exc)) from exc

    state.pop("_context", None)  # internal cache — see ml/docs/integration.md §4
    return state


@router.post(
    "/insights/ml-refresh",
    summary="Retrain the ML layer against the current database (call after reseeding)",
)
def ml_refresh(db: Session = Depends(get_db)):
    try:
        bundle = ml_bridge.refresh_ml_cache(db)
    except ml_bridge.MLNotReadyError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    return {"refreshed": True, "model_name": bundle.model_name, "metrics": bundle.metrics}
