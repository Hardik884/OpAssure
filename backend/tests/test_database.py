"""Seed a throwaway PostgreSQL database and verify it.

Uses TEST_DATABASE_URL (never DATABASE_URL, so running tests cannot wipe your dev
data). Skipped when TEST_DATABASE_URL is unset or unreachable.
"""

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.core.config import get_test_database_url
from app.db.session import make_engine
from app.models import GroundTruthLabel, Machine, Operator, Task, Telemetry
from simulator.seed import seed, verify


@pytest.fixture(scope="module")
def engine():
    url = get_test_database_url()
    if not url:
        pytest.skip("TEST_DATABASE_URL not set")
    eng = make_engine(url)
    try:
        with eng.connect() as conn:
            conn.execute(text("SELECT 1"))
    except OperationalError as exc:
        pytest.skip(f"test database unreachable: {exc.orig}")
    seed(eng)
    yield eng
    eng.dispose()


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
