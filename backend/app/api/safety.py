from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.core.errors import NotFoundError
from app.db.session import get_db
from app.models import Machine
from app.schemas.events import SafetyStateOut
from app.services.safety_state_service import safety_state

router = APIRouter(tags=["safety"])


@router.get("/safety/{machine_id}", response_model=SafetyStateOut, summary="Current safety state")
def get_safety(machine_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Machine, machine_id, "machine")
    state = safety_state(db, machine_id)
    if state is None:
        raise NotFoundError("telemetry", machine_id)
    return state
