"""Shared fixtures. DB tests use TEST_DATABASE_URL only (reseeded here), never DATABASE_URL."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.config import get_test_database_url
from app.db.session import get_db, make_engine
from app.main import app
from app.services.telemetry_service import live_store
from simulator.seed import seed


@pytest.fixture(scope="session")
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


@pytest.fixture()
def client(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    live_store.clear()
    yield TestClient(app)
    live_store.clear()
    app.dependency_overrides.pop(get_db, None)
