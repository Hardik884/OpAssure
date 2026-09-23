# OpAssure — Backend

**Owner:** Backend developer
**Stack:** Python, FastAPI, PostgreSQL (SQLAlchemy 2), WebSockets

> Status: data foundation + all RED REST APIs (operators, tasks, telemetry, safety,
> incidents with telemetry snapshot, training, insights, unified ML input, weather with
> synthetic fallback), T001 telemetry replay and WebSocket events (`WS /ws`).
> API + WebSocket contracts: [`docs/api/README.md`](../docs/api/README.md).

## Structure

| Path                           | Purpose                                                              |
| ------------------------------ | -------------------------------------------------------------------- |
| `app/main.py`                  | FastAPI app entrypoint (`GET /health`).                              |
| `app/api/`                     | HTTP routers, one per area (operators, tasks, telemetry, …).         |
| `app/models/`                  | SQLAlchemy ORM models: the 10 tables (see below).                    |
| `app/schemas/`                 | Request/response schemas (Pydantic).                                 |
| `app/services/safety_service.py` | Deterministic safety rules (seatbelt, proximity, idle, unattended). |
| `app/services/telemetry_service.py` | Telemetry queries + live store (60 s Black Box buffer). Replay feeds `live_store.ingest()`. |
| `app/services/weather_service.py` | Weather interface: synthetic by default, optional live API with fallback. |
| `app/services/insights_service.py` | Operator metrics + deterministic habit detection.                |
| `app/services/*`               | Tasks, incidents, training, safety state, ML input payload.          |
| `app/core/errors.py`           | Uniform JSON errors (no SQL/tracebacks to clients).                  |
| `app/services/replay_service.py` | T001 replay loop: DB rows -> live store -> safety/proximity/ETA/habit -> events. |
| `app/services/eta_service.py`  | Deterministic ETA fallback (swap in the ML model here).              |
| `app/api/demo.py`              | `POST /demo/start|stop|reset`, `GET /demo/status`.                   |
| `app/websocket/`               | `WS /ws` route, connection manager, event payload builders.          |
| `app/db/session.py`            | Engine / session setup from `DATABASE_URL`.                          |
| `app/db/init_db.py`            | Create or reset the schema.                                          |
| `app/core/config.py`           | Environment configuration (`.env` loading).                          |
| `simulator/generate_data.py`   | Deterministic synthetic data generator.                              |
| `simulator/scenarios.py`       | The scripted demo scenario (OP1001 / EXC001 / T001).                 |
| `simulator/seed.py`            | Reset DB + load synthetic data + verify.                             |
| `simulator/replay.py`          | CLI: connect to `/ws`, start the replay, print live events.         |
| `migrations/`                  | How the schema is managed (see its README).                          |
| `tests/`                       | Backend tests.                                                       |

## Quick start (exact commands)

All commands run from the `backend/` directory unless noted.

### 1. Install dependencies

```bash
cd backend
python -m venv .venv
# macOS/Linux:
source .venv/bin/activate
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Start PostgreSQL and configure `DATABASE_URL`

Option A — Docker (from the **repo root**):

```bash
cp .env.example .env             # example values already match docker-compose
docker compose up -d db
docker compose exec db createdb -U opassure opassure_test   # only needed for DB tests
```

Option B — an existing local PostgreSQL:

```bash
psql -U postgres -c "CREATE USER opassure WITH PASSWORD 'opassure' CREATEDB;"
psql -U postgres -c "CREATE DATABASE opassure OWNER opassure;"
psql -U postgres -c "CREATE DATABASE opassure_test OWNER opassure;"
cp ../.env.example ../.env       # or create backend/.env
```

The backend reads `DATABASE_URL` from the environment, `backend/.env`, or the
repo-root `.env` (first one wins):

```
DATABASE_URL=postgresql+psycopg2://opassure:opassure@localhost:5432/opassure
TEST_DATABASE_URL=postgresql+psycopg2://opassure:opassure@localhost:5432/opassure_test
CORS_ORIGINS=http://localhost:3000
```

Optional: `DEMO_DATE` (override "today"), `WEATHER_MODE=live` + `WEATHER_API_URL`
(external weather; falls back to synthetic automatically on any failure).

### 3. Create / reset the database

```bash
python -m app.db.init_db --reset    # drop + recreate all tables, empty
```

(Optional — step 4 does this for you.)

### 4. Seed data

```bash
python -m simulator.seed            # reset + load synthetic data + verify (~10 s)
python -m simulator.seed --verify-only   # re-check an existing database
```

This is the known-good demo reset: run it any time to get back to the exact same
state. It ends with `VERIFY: PASS` and exits non-zero if any check fails.

### 5. Start FastAPI

```bash
uvicorn app.main:app --reload
```

### 6. Open Swagger

- Swagger UI: http://localhost:8000/docs
- Demo path: `/tasks/today?operator_id=OP1001` → `/tasks/T001` → `/telemetry/latest/EXC001`
  → `/safety/EXC001` → `POST /incidents` → `/training/recommendations/OP1001` →
  `/ml-input/operator/OP1001`
- Health: http://localhost:8000/health → `{"status": "ok", "database": "ok"}`
  (`database` is `not_configured` / `unavailable` when the DB is missing).

### 7. Run the live demo (replay + WebSocket)

With the server running, in a second terminal (from `backend/`):

```bash
python -m simulator.replay                  # starts the T001 replay and prints every event
python -m simulator.replay --interval 1 --quiet   # faster, hide telemetry_update lines
```

Or from Swagger / curl: `curl -X POST localhost:8000/demo/start` (then `/demo/stop`,
`/demo/reset`, `/demo/status`); the frontend connects to `ws://localhost:8000/ws`.
`REPLAY_INTERVAL_SECONDS` (default 3) sets the pace.

### Tests

```bash
pytest
```

DB tests use `TEST_DATABASE_URL` only (they wipe and reseed that database) and are
skipped if it is not set. Generator and safety-rule tests need no database.

## Synthetic dataset

`python -m simulator.generate_data` prints row counts without touching the DB.
Same seed → identical data every run (checked by `tests/test_generate_data.py`).

| Table                 | Rows (seed 20250501) | Notes |
| --------------------- | -------------------: | ----- |
| `operators`           | 20     | OP1001–OP1020; 6 Beginner / 8 Intermediate / 6 Expert |
| `machines`            | 8      | EXC001–EXC005 excavators, LDR001–LDR003 loaders, ages 2–12 y |
| `weather`             | 1,440  | hourly, 2025-05-01 → 2025-06-29 |
| `tasks`               | 4,007  | 3,932 completed (history) + 75 scheduled on demo day |
| `telemetry`           | 25,408 | every 5–15 min + event rows on seatbelt changes; T001 at 1 min |
| `worker_positions`    | 44,003 | 12 workers, every 10 min in shift; 1-min tracks for near misses |
| `near_misses`         | 12     | W04 in EXC001's swing zone |
| `incidents`           | 13     | harsh events + reported near misses, with telemetry snapshot |
| `ground_truth_labels` | 992    | one row per planted case |
| `training_events`     | 4      | with before/after metrics |

The last day (2025-06-29) is **demo day** — "today" for the Mission Board. Its
tasks are `scheduled` (no actuals) except that T001 has scripted replay
telemetry. See `docs/architecture/backend-data-foundation.md` for the field
conventions, planted problems and demo script.
