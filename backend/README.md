# OpAssure — Backend

**Owner:** Backend developer
**Stack:** Python, FastAPI, PostgreSQL, WebSockets

> Status: skeleton only. The sole endpoint is `GET /health`.

## Structure

| Path              | Purpose                                                        |
| ----------------- | -------------------------------------------------------------- |
| `app/main.py`     | FastAPI app entrypoint.                                        |
| `app/api/`        | HTTP route handlers (routers).                                 |
| `app/models/`     | Database (ORM) models.                                         |
| `app/schemas/`    | Request/response schemas (Pydantic).                           |
| `app/services/`   | Business logic; integration point with `/ml`.                  |
| `app/websocket/`  | Realtime WebSocket endpoints and connection management.        |
| `app/db/`         | Database session/connection setup.                             |
| `app/core/`       | Configuration, settings, shared constants.                     |
| `app/utils/`      | Generic helpers.                                               |
| `simulator/`      | Synthetic telemetry generation, scenarios, and replay.         |
| `migrations/`     | Database migrations.                                           |
| `tests/`          | Backend unit tests.                                            |

## Local development

```bash
cd backend
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Then open http://localhost:8000/health.
