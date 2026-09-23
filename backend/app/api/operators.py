from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_or_404, history_cutoff
from app.db.session import get_db
from app.models import Operator
from app.schemas.core import OperatorOut
from app.schemas.insights import InsightsOut
from app.services.insights_service import operator_insights

router = APIRouter(tags=["operators"])


@router.get("/operators", response_model=list[OperatorOut], summary="List operators")
def list_operators(db: Session = Depends(get_db)):
    return db.scalars(select(Operator).order_by(Operator.operator_id)).all()


@router.get("/operators/{operator_id}", response_model=OperatorOut, summary="Single operator")
def get_operator(operator_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Operator, operator_id, "operator")


@router.get("/operator/{operator_id}/insights", response_model=InsightsOut, summary="Operator Twin data")
def get_insights(operator_id: str, db: Session = Depends(get_db)):
    operator = get_or_404(db, Operator, operator_id, "operator")
    return operator_insights(db, operator, history_cutoff(db))
