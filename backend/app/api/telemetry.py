from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Machine
from app.schemas.core import LatestTelemetryOut, TelemetryHistoryOut
from app.services import telemetry_service

router = APIRouter(tags=["telemetry"])


@router.get("/telemetry/latest/{machine_id}", response_model=LatestTelemetryOut, summary="Latest telemetry")
def latest(machine_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Machine, machine_id, "machine")
    row, source = telemetry_service.get_latest(db, machine_id)
    if row is None:
        raise NotFoundError("telemetry", machine_id)
    return {**row, "source": source}


@router.get("/telemetry/history/{machine_id}", response_model=TelemetryHistoryOut, summary="Telemetry history")
def history(machine_id: str,
            limit: int = Query(200, ge=1, le=5000, description="Most recent N rows (returned oldest first)"),
            task_id: str | None = Query(None, description="Only rows for this task"),
            db: Session = Depends(get_db)):
    get_or_404(db, Machine, machine_id, "machine")
    rows = telemetry_service.history(db, machine_id, limit, task_id)
    if not rows:
        raise NotFoundError("telemetry", machine_id if not task_id else f"{machine_id}/{task_id}")
    return {"machine_id": machine_id, "count": len(rows), "rows": rows}
