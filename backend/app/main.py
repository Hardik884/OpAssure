"""OpAssure backend entrypoint.

Only a health check is exposed for now. Feature routers will be added under app/api/.
"""

import logging

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import DatabaseNotConfiguredError, get_engine

logger = logging.getLogger(__name__)

app = FastAPI(title="OpAssure API", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    """API liveness plus database reachability (ok | not_configured | unavailable)."""
    try:
        with get_engine().connect() as conn:
            conn.execute(text("SELECT 1"))
        database = "ok"
    except DatabaseNotConfiguredError:
        database = "not_configured"
    except SQLAlchemyError as exc:
        logger.warning("Database health check failed: %s", exc)
        database = "unavailable"
    return {"status": "ok", "database": database}
