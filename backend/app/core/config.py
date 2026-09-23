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
