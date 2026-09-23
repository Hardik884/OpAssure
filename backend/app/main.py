"""OpAssure backend entrypoint: REST API for the frontend and the AI/ML layer.

Contracts are documented in docs/api/README.md; Swagger UI is served at /docs.
"""

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.api import incidents, machines, ml_input, operators, safety, tasks, telemetry, training, weather
from app.core.config import get_cors_origins
from app.core.errors import register_error_handlers
from app.db.session import DatabaseNotConfiguredError, get_engine

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

app = FastAPI(title="OpAssure API", version="0.2.0")

cors_origins = get_cors_origins()
if cors_origins:
    app.add_middleware(CORSMiddleware, allow_origins=cors_origins, allow_credentials=True,
                       allow_methods=["*"], allow_headers=["*"])
else:
    logger.warning("CORS_ORIGINS is not set; browser clients on other origins will be blocked")

register_error_handlers(app)
for module in (operators, machines, tasks, telemetry, safety, incidents, training, weather, ml_input):
    app.include_router(module.router)


@app.get("/health", tags=["health"])
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
