from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_or_404, history_cutoff
from app.db.session import get_db
from app.models import Operator
from app.schemas.events import RecommendationsOut, TrainingCompleteIn, TrainingCompleteOut
from app.services import training_service

router = APIRouter(tags=["training"])


@router.get("/training/recommendations/{operator_id}", response_model=RecommendationsOut,
            summary="Training recommendations")
def recommendations(operator_id: str, db: Session = Depends(get_db)):
    operator = get_or_404(db, Operator, operator_id, "operator")
    return training_service.recommendations(db, operator, history_cutoff(db))


@router.post("/training/complete", response_model=TrainingCompleteOut, summary="Record training completion")
def complete(payload: TrainingCompleteIn, db: Session = Depends(get_db)):
    operator = get_or_404(db, Operator, payload.operator_id, "operator")
    event, created = training_service.complete(db, operator, payload.clip_id, history_cutoff(db),
                                               payload.timestamp, payload.before_metric, payload.after_metric)
    return {"training_event": event, "created": created}
