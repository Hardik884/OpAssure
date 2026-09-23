# OpAssure

OpAssure is an intelligent operator assistant for Caterpillar (CAT) machinery, being built for the Caterpillar Hackathon. It aims to give equipment operators a single real-time companion that plans their daily work, keeps them safe on site, coaches them to improve, flags unusual machine or operator behaviour, and estimates how long each task will take — driven by machine telemetry, operator history, and site context.

> **Status:** Backend data foundation in place (PostgreSQL schema, deterministic synthetic dataset, seed/reset, `/health`). Feature APIs, replay, frontend and ML are not implemented yet.

## Problem

Smart Operator Assistant for CAT machinery.

## Core Outcomes

1. **Daily task dashboard** — a clear view of the operator's assigned work for the day.
2. **Safety** — timely, context-aware safety alerts and guidance.
3. **Operator training** — personalised coaching based on how the operator actually works.
4. **Unusual behaviour detection** — spotting anomalies in machine telemetry and operating patterns.
5. **Task time estimation** — predicting how long a task will take (ETA).

## Architecture

```
Frontend  ->  Backend  ->  AI/ML  ->  Database / Data
(Next.js)     (FastAPI)    (Python)   (PostgreSQL, synthetic telemetry)
                 |
             WebSockets (realtime updates to the frontend)
```

| Layer          | Technology                      |
| -------------- | ------------------------------- |
| Frontend       | Next.js, React, TypeScript      |
| Backend        | Python, FastAPI                 |
| AI/ML          | Python                          |
| Database       | PostgreSQL                      |
| Realtime       | WebSockets                      |
| Synthetic data | Python                          |

## Team Ownership

| Area     | Owner                | Directory    |
| -------- | -------------------- | ------------ |
| Frontend | Frontend developer   | `/frontend`  |
| Backend  | Backend developer    | `/backend`   |
| AI/ML    | AI/ML developer      | `/ml`        |

Each developer works inside their own directory. Shared directories (`/data`, `/docs`, `/scripts`, `/tests`) are coordinated across the team.

## Repository Structure

| Path                 | Purpose                                                                 |
| -------------------- | ----------------------------------------------------------------------- |
| `frontend/`          | Next.js + React + TypeScript operator UI.                               |
| `backend/`           | FastAPI service, WebSocket server, DB access, and telemetry simulator.  |
| `ml/`                | ML models: operator twin, ETA, anomaly detection, safety, training.     |
| `data/`              | Datasets: `raw/`, `processed/`, `synthetic/`, `ground_truth/`.          |
| `docs/`              | Architecture, API, ML, and demo documentation.                          |
| `scripts/`           | Cross-cutting helper scripts (setup, data, demo).                       |
| `tests/`             | Cross-component / integration tests.                                    |
| `.github/workflows/` | GitHub Actions workflows (none yet).                                    |
| `docker-compose.yml` | Local PostgreSQL for development.                                       |
| `.env.example`       | Template for required environment variables.                            |

## Getting Started

```bash
cp .env.example .env        # fill in local values — never commit .env
docker compose up -d db     # start local PostgreSQL
```

Per-component setup instructions live in each component's README:
[`frontend/`](frontend/README.md), [`backend/`](backend/README.md), [`ml/`](ml/README.md).

## Branching

- `main` — stable, demo-ready code.
- `develop` — integration branch. Open pull requests into `develop`.
- Feature branches (e.g. `feature/frontend-mission-board`) branch off `develop`.

## Development Rule

**Build the MVP first.** The five required outcomes come before any advanced features.

## Demo Strategy

The final demo will replay synthetic telemetry and show the operator experience in real time.

## License

[MIT](LICENSE)
