from datetime import date

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.db.session import get_db
from app.models import Operator, Task
from app.schemas.core import TaskOut, TodayTasksOut
from app.services import task_service

router = APIRouter(tags=["tasks"])


@router.get("/tasks/today", response_model=TodayTasksOut, summary="Today's tasks for an operator")
def tasks_today(operator_id: str = Query(..., examples=["OP1001"]),
                date: date | None = Query(None, description="Override the demo day (YYYY-MM-DD)"),
                db: Session = Depends(get_db)):
    get_or_404(db, Operator, operator_id, "operator")
    day = date or task_service.get_today(db)
    return {"date": day, "operator_id": operator_id, "tasks": task_service.tasks_for_day(db, operator_id, day)}


@router.get("/tasks/{task_id}", response_model=TaskOut, summary="Single task")
def get_task(task_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Task, task_id, "task")
