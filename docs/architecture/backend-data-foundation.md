# Backend data foundation

Decisions and conventions behind the PostgreSQL schema and synthetic dataset.
Commands are in [`backend/README.md`](../../backend/README.md).

## Schema

Defined by SQLAlchemy models in `backend/app/models/`; created with
`Base.metadata.create_all` (no Alembic — the DB is always rebuilt by
`python -m simulator.seed`). Field names follow the handover / CLAUDE.md §6.

Columns **added** beyond the handover field list (additive only, nothing renamed):

| Table | Added | Why |
| --- | --- | --- |
| `machines` | `model` | display name ("CAT 320") |
| `tasks` | `status` (`completed` / `scheduled`) | Mission Board needs to know what is still to do |
| `telemetry` | `id`, `task_id` | replay reads one task's rows in order |
| `incidents` | `id`, `task_id`, `severity`, `telemetry_snapshot` (JSON), `source` | Incident Black Box |
| `near_misses` | `id`, `worker_id`, `distance_m`, `direction`, `severity` | Proximity Guard |
| `ground_truth_labels` | `problem`, `operator_id`, `machine_id`, `worker_id`, `task_id`, `timestamp`, `expected_detection`, `description` | "who, when, what" |
| `training_events` | `id`, `metric_name` | says what before/after_metric measure |

## Field conventions

- Timestamps are naive **site-local** time.
- Units: `temperature` °C, `rain_mm` mm per hour, `wind_speed` km/h, `volume_m3` m³,
  `fuel_used_l` litres, `*_time_min` minutes, `avg_cycle_time_s` seconds.
- **Telemetry interval fields** (`fuel_used_l`, `load_cycles`, `avg_cycle_time_s`,
  `cycle_time_std`, `idling_time_min`, `idle_reason`, `harsh_events`) cover the
  period since the previous row of the same task. `seatbelt_status`,
  `machine_moving`, `lat`/`lon` are the state at `timestamp`. `engine_hours` is
  the machine's cumulative meter.
- `avg_cycle_time_s` / `cycle_time_std` are null when the interval was all idle.
- `idle_reason`: null, `truck_wait` (legitimate) or `avoidable` (operator).
- `seatbelt_status`: `fastened` / `unfastened`.
- `safety_alert`: null or `seatbelt_unfastened_while_moving` (critical),
  `possible_unattended_machine` (warning), `avoidable_idle` (warning) — computed
  by `app/services/safety_service.py`, the same rules replay will use.
- `tasks.estimated_time_min` is a naive plan (standard cycle time + 15%); it is
  the baseline the ML ETA should beat. `actual_time_min` is null until completed.
- Proximity bands: ≤15 m critical, ≤30 m caution, otherwise safe. Direction is
  relative to the machine, assumed to face north.

## Dataset shape

Seed `20250501`, 60 days from 2025-05-01. Two half-shifts per day (07:00–12:00,
12:30–17:00); each half-shift every machine gets an operator, so operators rotate
across machines — needed to separate machine effects from operator effects. Each
task is simulated minute by minute and then sampled into telemetry.

**Day 60 (2025-06-29) is demo day**: its tasks are `scheduled` with no actuals.
T001 (07:30, OP1001 on EXC001) has scripted 1-minute replay telemetry
(`backend/simulator/scenarios.py`). **ML must not train on demo-day rows.**

## Planted problems → `ground_truth_labels.problem`

| problem | Planted behaviour | Label granularity |
| --- | --- | --- |
| `seatbelt_pattern` | OP1001 unbuckles in truck waits ≥5 min (p=0.65); moves before re-buckling 55% of those times | each unbuckle / unbelted-move event |
| `afternoon_slowdown` | OP1001, OP1012: cycle time +6% per hour after 14:00, up to ×2.5 that on hot (34 °C) afternoons | each operator-day worked in the afternoon |
| `machine_degradation` | EXC003: fuel +0.6%/day, cycle time +0.3%/day, whoever operates it | each day EXC003 works; `expected_detection` false before day 20 |
| `operator_inefficiency` | OP1015 burns 40% extra fuel on every machine | each OP1015 task |
| `legitimate_idle` | 10 truck-shortage days → 10–25 min truck waits (`idle_reason=truck_wait`) | each wait ≥8 min; must **not** be blamed on the operator |
| `proximity_near_miss` | worker W04 walks into EXC001's swing zone (8–14 m), 12 times | each event (also in `near_misses`) |

Demo T001 events are labelled too. Operators other than OP1001 have small
belt-skip probabilities (≤4%), so a few incidental unbelted rows exist — noise,
not labelled as a habit.

Training: OP1003 and OP1008 (avoidable idle, day 30) and OP1016 (harsh events,
day 35) completed training, and their later behaviour improves. OP1011's
training is recommended but not completed.
