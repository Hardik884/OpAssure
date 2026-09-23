from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.db.session import get_db
from app.models import Operator
from app.schemas.events import IncidentCreate, IncidentCreatedOut, IncidentListOut
from app.services import incident_service

router = APIRouter(tags=["incidents"])


@router.post("/incidents", response_model=IncidentCreatedOut, status_code=201,
             summary="Create incident (saves a recent telemetry snapshot)")
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)):
    return incident_service.create_incident(db, payload)


@router.get("/incidents/{operator_id}", response_model=IncidentListOut, summary="Incident history, newest first")
def list_incidents(operator_id: str, db: Session = Depends(get_db)):
    get_or_404(db, Operator, operator_id, "operator")
    incidents = incident_service.incidents_for_operator(db, operator_id)
    return {"operator_id": operator_id, "count": len(incidents), "incidents": incidents}
