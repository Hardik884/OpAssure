"""Runtime configuration, read from environment variables.

`.env` files are loaded from `backend/.env` first, then the repo-root `.env`
(already-set variables are never overridden). Nothing is hardcoded here — see
`.env.example` at the repo root for the variables in use.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parent

load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


def get_database_url() -> str | None:
    """Main application database (DATABASE_URL). None when unset."""
    return os.getenv("DATABASE_URL") or None


def get_test_database_url() -> str | None:
    """Throwaway database for the DB tests (TEST_DATABASE_URL). None when unset."""
    return os.getenv("TEST_DATABASE_URL") or None


def get_cors_origins() -> list[str]:
    """Comma-separated CORS_ORIGINS, e.g. "http://localhost:3000". Empty -> no CORS."""
    return [o.strip() for o in os.getenv("CORS_ORIGINS", "").split(",") if o.strip()]


def get_demo_date() -> str | None:
    """DEMO_DATE (YYYY-MM-DD) overrides "today". Unset -> the latest task date in the DB."""
    return os.getenv("DEMO_DATE") or None


def get_weather_mode() -> str:
    """WEATHER_MODE: "synthetic" (default, fully offline) or "live" (external API + fallback)."""
    return (os.getenv("WEATHER_MODE") or "synthetic").strip().lower()


def get_weather_api_url() -> str | None:
    """WEATHER_API_URL: an Open-Meteo-compatible hourly endpoint. Only used in live mode."""
    return os.getenv("WEATHER_API_URL") or None
