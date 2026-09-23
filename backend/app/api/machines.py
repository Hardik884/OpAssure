from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import get_or_404
from app.db.session import get_db
from app.models import Machine
from app.schemas.core import MachineOut

router = APIRouter(tags=["machines"])


@router.get("/machines", response_model=list[MachineOut], summary="List machines")
def list_machines(db: Session = Depends(get_db)):
    return db.scalars(select(Machine).order_by(Machine.machine_id)).all()


@router.get("/machines/{machine_id}", response_model=MachineOut, summary="Single machine")
def get_machine(machine_id: str, db: Session = Depends(get_db)):
    return get_or_404(db, Machine, machine_id, "machine")
