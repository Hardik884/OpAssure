# OpAssure — Project Instructions for Claude Code

This file is the persistent source of truth for working on OpAssure. Read it before
making changes. It states stable facts (architecture, contracts, priorities, rules).
Reusable procedures (checklists, evaluation runs, review steps) live in
`.claude/skills/` and are invoked as slash commands — this file does not duplicate them.

## 1. Product Overview

**OpAssure** is an intelligent operator companion for CAT construction machinery.
It supports the operator throughout the workday using machine telemetry, environmental
data, and a personalized **Operator Twin** — a data-driven profile of how a specific
operator works.

Central idea: **treat every machine operator like a professional athlete** — pre-game
briefing, live performance monitoring, coaching, post-game review.

The Operator Twin is an intelligence layer, not a standalone dashboard. It should make
the ETA, safety, training, and anomaly-detection features smarter — it is never the
product's only screen.

### Product principles (apply to every feature decision)

1. **Operator-first.** Built for the operator in the cab, not primarily a manager
   analytics tool. Managers may eventually get summaries; the operator experience
   comes first.
2. **One-second glance.** Critical info must be understood instantly: large numbers,
   green/amber/red states, short explanations, large touch targets, tablet/phone-friendly.
3. **Private by default.** Operator behavioral data is operator-owned unless a feature
   explicitly requires sharing it.
4. **Software only.** No new hardware. Use existing machine telemetry, weather data,
   browser/device capabilities, and phone/tablet location where relevant.
5. **Explainability.** Numeric results come from deterministic logic, statistics, or ML
   models. An LLM may phrase a natural-language explanation but must **never invent or
   alter the underlying numeric result**.
6. **Deterministic demo.** The project must have a repeatable synthetic demo scenario
   (see §7) that produces the same outcomes every run.
7. **MVP first.** A complete, working implementation of the five mandatory outcomes
   beats sophisticated optional features. See the priority system in §8.

## 2. The Five Mandatory Outcomes → OpAssure Feature Mapping

The hackathon brief is "Smart Operator Assistant for CAT machinery" with exactly five
required outcomes. Every mandatory outcome must keep working; optional features must
never compromise one of these.

| # | Mandatory outcome | OpAssure implementation |
|---|---|---|
| 1 | Daily task dashboard | Mission Board, smart task ordering, weather-aware task context, machine-condition context, operator-aware task context, Pre-Task Threat Briefing |
| 2 | Safety (seatbelt compliance, proximity hazards, incident logging, working conditions) | Seatbelt Truth Check, Proximity Guard, Incident Black Box, weather/working-condition awareness, critical alerts, quiet mode |
| 3 | Operator training hub | Training Hub, Just-in-Time Micro Training, instructor escalation, browser-based scenario simulator |
| 4 | Unusual machine/operator behaviour (excessive idling, unsafe patterns) | Habit Radar, Idle Shield, Focus Battery, machine-vs-operator diagnosis |
| 5 | Task time estimation (historical data + environmental conditions) | Personal ETA, ETA range, continuously updating ETA, delay explanation, Bucket Countdown, two-way issue reporting |

Additional end-of-shift / site features (Level 3, optional): Game Tape, Site
Breadcrumbs.

## 3. Architecture

```
Frontend (Next.js/React/TS) <-- WebSockets/REST --> Backend (FastAPI) <--> ML (Python)
                                                          |
                                                    PostgreSQL
```

| Layer | Stack |
|---|---|
| Frontend | Next.js, React, TypeScript, Tailwind CSS, shadcn/ui (where useful), Recharts (where useful), Leaflet (where useful), PWA, IndexedDB |
| Backend | Python, FastAPI, PostgreSQL, WebSockets, Docker; optional TimescaleDB; optional MQTT if time permits |
| ML | Python, pandas, numpy, scikit-learn; LightGBM/statsmodels/ruptures/SHAP where useful; PyMC only if genuinely useful and time allows |
| Synthetic data | Python, NumPy, Pandas, Faker; SimPy if useful |
| Weather | Open-Meteo when available — **always keep a synthetic/local fallback** |
| LLM | Optional. Never make core functionality depend on an LLM API being available. Used only for natural-language phrasing of numbers already computed elsewhere (see §1.5). |

## 4. Repository Structure

```
opassure/
├── frontend/            Next.js app (owned by Frontend dev) — see frontend/README.md
├── backend/              FastAPI app + simulator (owned by Backend dev) — see backend/README.md
├── ml/                    Models + feature engineering (owned by ML dev) — see ml/README.md
├── data/
│   ├── raw/               Ingested/source data (git-ignored contents)
│   ├── processed/         Cleaned/derived data (git-ignored contents)
│   ├── synthetic/         Generated synthetic dataset (tracked)
│   └── ground_truth/      Labels for planted anomalies (tracked)
├── docs/
│   ├── architecture/      System diagrams, data flow, deployment
│   ├── api/                REST + WebSocket contracts
│   ├── ml/                  Model cards, feature defs, evaluation results
│   └── demo/                Demo script, scenarios, run instructions
├── scripts/               Cross-cutting helper scripts
├── tests/                 Cross-component / integration tests
├── .github/workflows/     CI (minimal for now)
├── .claude/skills/        Project-level Claude Code skills (see §11)
├── .env.example
├── .gitignore
├── README.md
├── CLAUDE.md              This file
└── docker-compose.yml     Local PostgreSQL
```

Component-level details (setup, subfolder purpose) live in each component's own
README — don't duplicate them here.

## 5. Team Ownership

| Person | Owns | Responsibilities |
|---|---|---|
| **Person 1 — Frontend/PWA/UX** | `/frontend` | Pages, components, operator workflow, responsive UI, PWA, visualizations |
| **Person 2 — Backend/Data/Realtime** | `/backend` | PostgreSQL, synthetic data, APIs, telemetry replay, WebSockets, incident storage, worker-position simulation, backend safety rules |
| **Person 3 — AI/ML** | `/ml` | Feature engineering, ETA, Operator Twin, Habit Radar, Idle Shield, Focus Battery, risk intelligence, training recommendation, evaluation |

Shared directories (`data/`, `docs/`, `scripts/`, `tests/`, root config) are
cross-team — coordinate before restructuring them. All three areas integrate into one
product; see §10 for integration rules.

## 6. Data Model

Synthetic dataset scale: **20 operators, 8 machines, 60 days.**

### Core tables

- `operators`, `machines`, `weather`, `tasks`, `telemetry`, `worker_positions`,
  `incidents`, `near_misses`, `ground_truth_labels`, `training_events`

### Key fields

**operators**: `operator_id`, `name`, `skill`, `base_speed`, `fatigue_start_hour`,
`heat_sensitivity`, `rain_sensitivity`, `belt_skip_probability_when_idle`

**machines**: `machine_id`, `type`, `age_years`, `health_drift`

**weather**: `timestamp`, `condition`, `temperature`, `rain_mm`, `wind_speed`

**tasks**: `task_id`, `task_type`, `zone`, `volume_m3`, `estimated_buckets`, `weather`,
`operator_id`, `operator_skill`, `machine_id`, `machine_age`, `estimated_time_min`,
`actual_time_min`, `start_time`

**telemetry**: `timestamp`, `machine_id`, `operator_id`, `engine_hours`, `fuel_used_l`,
`load_cycles`, `avg_cycle_time_s`, `cycle_time_std`, `idling_time_min`, `idle_reason`,
`seatbelt_status`, `machine_moving`, `harsh_events`, `lat`, `lon`, `safety_alert`

**worker_positions**: `timestamp`, `worker_id`, `lat`, `lon`

### Planted synthetic problems (must exist, with ground-truth labels)

1. **Seatbelt habit** — operator unbuckles during long truck waits, sometimes starts
   moving before re-buckling.
2. **Afternoon slowdown** — pace drops after ~2–3 PM, worsens with heat.
3. **Machine degradation** — one machine gradually gets less efficient; fuel/cycle
   time rises for *every* operator who uses it.
4. **Operator inefficiency** — one operator consistently burns more fuel across
   multiple machines.
5. **Legitimate idle** — waiting for trucks causes long idle; this must **not** be
   attributed to the operator as a fault.
6. **Proximity near-misses** — workers repeatedly enter a machine's swing-zone area.

Every planted problem needs a corresponding row in `ground_truth_labels` so detection
can be evaluated (`/ml-evaluation`, `/data-validation`).

## 7. Demo Scenario

Deterministic primary demo identifiers — every team member must be able to reproduce
the same scenario with these IDs:

- Operator: `OP1001`
- Machine: `EXC001`
- Task: `T001`

### Demo story (end-to-end)

```
Operator logs in
  -> Mission Board
  -> Today's task selected
  -> Pre-Task Threat Briefing
  -> Task starts, live telemetry begins
  -> ETA shown
  -> Weather changes / cycle time changes -> ETA updates
  -> Worker enters swing zone -> Proximity warning
  -> Operator reports incident, recent telemetry attached
  -> Repeated behaviour detected -> Just-in-Time training recommendation
  -> Operator completes training
  -> Future behaviour is measured
  -> End-of-shift summary
```

Use `/demo-check` to verify the whole path is currently reproducible.

## 8. Priority System

**Never sacrifice a lower level number for a higher one.** When time is short, cut
Level 3, then Level 2 — Level 1 must always work for the demo. Use `/feature-priority`
to classify any new feature request before starting it.

### Level 1 — MUST WORK
Application shell, PostgreSQL, synthetic data, backend APIs, Mission Board, Active
Task, basic ETA, seatbelt safety, proximity safety, incident logging, Training Hub,
telemetry replay, WebSockets, end-to-end integration.

### Level 2 — IMPORTANT
Operator Twin, personal ETA, dynamic ETA, Habit Radar, Idle Shield, Focus Battery,
Just-in-Time Micro Training, Pre-Task Threat Briefing.

### Level 3 — OPTIONAL / LAST
Game Tape, Site Breadcrumbs, 3D simulator, advanced offline synchronization, MQTT,
advanced TimescaleDB optimization, sophisticated animation, advanced LLM integration.

## 9. Engineering Rules

- Inspect the current repository before making changes.
- Reuse existing working code; do not rewrite working features unnecessarily.
- Do not invent APIs that conflict with existing contracts; keep interfaces stable.
- Prefer simple, reliable implementations over theoretical complexity.
- Do not hardcode fake model outputs in production paths. Mocks are fine during
  development but must be clearly separated from real logic (e.g. a `mock_` prefix,
  a distinct module, or a feature flag — never silently swapped in).
- Never commit secrets or `.env`. Never add unnecessary dependencies.
- Test important logic. Keep the project runnable locally at all times.
- Never claim functionality exists unless it actually works.
- Document major architectural decisions (in `docs/architecture/`).
- Prioritize the demo path (§7) over incidental polish.
- When blocked by an external service (e.g. Open-Meteo), implement a deterministic
  local fallback rather than blocking the feature.

## 10. Integration Rules (API / Data-Contract Principles)

- Field names must match the data model in §6 exactly across backend, ML, and
  frontend — no silent renames at a layer boundary.
- The backend is the single source of truth for REST/WebSocket contracts; document
  them in `docs/api/` as they're added.
- ML models are called by the backend as a service boundary (function call or
  internal API) — the backend owns request/response shaping to the frontend; ML
  should not talk to the frontend directly.
- WebSocket messages need a stable `type` field and a versioned, documented payload
  shape.
- Demo identifiers (`OP1001`, `EXC001`, `T001`) must resolve correctly across every
  layer — never assume they exist without checking.
- Local dev URLs and CORS config are driven by `.env` (see `.env.example`), never
  hardcoded into source.
- Use `/integration-check` before merging a change that touches a contract.

## 11. ML Principles

- Deterministic/statistical/ML models produce the numbers; an LLM (if used) only
  narrates them — see §1 principle 5.
- Avoid data leakage: never train on data that includes the ground-truth label or
  information from the future relative to the prediction point.
- Prefer reproducible, explainable models (e.g. gradient boosting + SHAP) over opaque
  ones unless there's a clear demo-quality reason otherwise.
- Every model needs an evaluation path against `data/ground_truth/` — see
  `/ml-evaluation`.
- Keep training/inference code separate from one-off notebook exploration
  (`ml/notebooks/` is for exploration, `ml/src/` is production code).

## 12. UI Principles

- Operator-first, one-second glance, large touch targets — see §1 principles 1–2.
- Color coding: green/amber/red for status, but never color-only — pair with an icon
  or short text (accessibility).
- Mobile/tablet layouts are not an afterthought — design for them from the start.
- Keep the component structure aligned with `frontend/src/components/<feature>/` —
  don't create a flat, unorganized component pile.

## 13. Testing Principles

- Test the logic that drives mandatory outcomes first (safety rules, ETA
  calculation, seatbelt detection) before optional features.
- Backend/ML: unit tests for deterministic logic; integration tests for
  API/WebSocket contracts.
- Frontend: prioritize tests for data-critical components (ETA display, safety
  alerts) over purely presentational ones.
- A failing test blocks a merge to `develop`; do not comment out or skip a test to
  make CI pass.

## 14. Do-Not-Overengineer Rules

- No new hardware, no unnecessary external services, no speculative abstraction
  layers "for future flexibility" during the hackathon window.
- Don't build a generic plugin/config system for something used once.
- Don't add a new dependency to save writing ~10 lines of code.
- Don't optimize for scale (sharding, multi-region, etc.) — this is a hackathon demo
  running locally/on one deployment target.
- If a Level 3 feature would require restructuring Level 1 code, it's not worth it —
  defer it.

## 15. Branching

- `main` — the working branch; commit and push directly to `main`, no PR required.
- `develop` — integration branch, kept for reference; no longer the required PR target.
- Feature branches (e.g. `feature/frontend-mission-board`) are optional.

## 16. Skills

Reusable procedures live in `.claude/skills/` and are invoked as slash commands:

- `/demo-check` — full demo-readiness checklist (§7).
- `/ml-evaluation` — run and evaluate ML models against ground truth (§11).
- `/data-validation` — validate the synthetic dataset (§6).
- `/integration-check` — check frontend/backend/ML contract compatibility (§10).
- `/code-review` — review a diff for bugs, contract breaks, complexity, security,
  regressions to mandatory outcomes (§9).
- `/feature-priority` — classify a proposed feature as Level 1/2/3 (§8).

Each skill's own `SKILL.md` has the actionable steps; this file has the stable facts
they refer back to.
