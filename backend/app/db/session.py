"""PostgreSQL connection layer (SQLAlchemy 2.x).

The engine is created lazily so the API process can start (and report
`database: not_configured` on /health) even before DATABASE_URL is set.
"""

from collections.abc import Iterator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_database_url

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


class DatabaseNotConfiguredError(RuntimeError):
    pass


def make_engine(url: str) -> Engine:
    connect_args = {"connect_timeout": 5} if url.startswith("postgresql") else {}
    return create_engine(url, pool_pre_ping=True, connect_args=connect_args)


def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_database_url()
        if not url:
            raise DatabaseNotConfiguredError(
                "DATABASE_URL is not set. Copy .env.example to .env and fill it in "
                "(see backend/README.md)."
            )
        _engine = make_engine(url)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _session_factory


def get_db() -> Iterator[Session]:
    """FastAPI dependency: one session per request."""
    session = get_session_factory()()
    try:
        yield session
    finally:
        session.close()
