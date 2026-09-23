"""Seeded throwaway database (see conftest.py): counts, demo IDs, reproducible reseed."""

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import GroundTruthLabel, Machine, Operator, Task, Telemetry
from simulator.seed import seed, verify


def test_verification_passes(engine):
    failures = [(name, detail) for name, ok, detail in verify(engine) if not ok]
    assert failures == []


def test_counts(engine):
    with Session(engine) as s:
        assert s.scalar(select(func.count()).select_from(Operator)) == 20
        assert s.scalar(select(func.count()).select_from(Machine)) == 8
        assert s.scalar(select(func.count()).select_from(Task)) > 1000
        assert s.scalar(select(func.count()).select_from(Telemetry)) > 10000


def test_demo_entities_exist(engine):
    with Session(engine) as s:
        assert s.get(Operator, "OP1001") is not None
        assert s.get(Machine, "EXC001") is not None
        task = s.get(Task, "T001")
        assert task is not None
        assert (task.operator_id, task.machine_id) == ("OP1001", "EXC001")


def test_reseed_is_reproducible(engine):
    def snapshot():
        with Session(engine) as s:
            return (
                s.scalar(select(func.count()).select_from(Telemetry)),
                s.scalar(select(func.sum(Telemetry.fuel_used_l))),
                s.scalar(select(func.count()).select_from(GroundTruthLabel)),
                s.scalar(select(Operator.name).where(Operator.operator_id == "OP1001")),
            )

    before = snapshot()
    seed(engine)
    assert snapshot() == before
