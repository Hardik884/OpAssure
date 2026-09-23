from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.schemas.insights import MLInputOut
from app.services.ml_input_service import build_ml_input

router = APIRouter(tags=["ml"])


@router.get("/ml-input/operator/{operator_id}", response_model=MLInputOut, summary="Unified AI/ML input payload")
def ml_input(operator_id: str,
             task_id: str | None = Query(None, description="Default: operator's current task today"),
             as_of: datetime | None = Query(None, description="Point in time; default: live replay time or task start"),
             db: Session = Depends(get_db)):
    return build_ml_input(db, operator_id, task_id, as_of)
