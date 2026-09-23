# OpAssure API contracts (v0.3)

The backend (FastAPI) is the single source of truth for these contracts. Swagger UI
with live schemas: **http://localhost:8000/docs**.

## Conventions

- Base URL: `http://localhost:8000` (frontend: `NEXT_PUBLIC_API_URL`).
- JSON in/out. Timestamps are ISO-8601, naive **site-local** time (e.g. `2025-06-29T07:30:00`).
- Field names are the database column names (see
  [`docs/architecture/backend-data-foundation.md`](../architecture/backend-data-foundation.md)
  for units). The only camelCase keys are the ones the handover defined: the
  top level of `/ml-input` and the WebSocket event payloads.
- **"Today"** is the demo day: `DEMO_DATE` if set, otherwise the latest task date in the
  DB (**2025-06-29** with the standard seed).
- Demo IDs: operator `OP1001`, machine `EXC001`, task `T001`.

### Errors

Every error has the same shape. Raw SQL and stack traces are never returned.

```json
{"error": "not_found", "message": "Operator OP9999 not found", "resource": "operator", "id": "OP9999"}
```

| Status | `error` | When |
| --- | --- | --- |
| 404 | `not_found` | unknown operator / machine / task, or a machine with no telemetry (`resource: "telemetry"`) |
| 422 | `validation_error` | malformed body or query (has `details: [{field, message}]`) |
| 422 | `invalid_request` | well-formed but inconsistent (unknown `clip_id`, task/operator mismatch, …) |
| 503 | `database_error` / `database_not_configured` | PostgreSQL down or unset |
| 500 | `internal_error` | anything unexpected (logged server-side) |

---

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Liveness + DB status |
| GET | `/operators` | List operators |
| GET | `/operators/{id}` | Single operator |
| GET | `/machines`, `/machines/{id}` | Machines |
| GET | `/tasks/today?operator_id=` | Today's tasks (Mission Board) |
| GET | `/tasks/{id}` | Single task |
| GET | `/telemetry/latest/{machine_id}` | Latest telemetry row |
| GET | `/telemetry/history/{machine_id}` | Telemetry history, oldest first |
| GET | `/safety/{machine_id}` | Current safety state |
| POST | `/incidents` | Create incident + telemetry snapshot |
| GET | `/incidents/{operator_id}` | Incident history |
| GET | `/training/recommendations/{operator_id}` | Training recommendations |
| POST | `/training/complete` | Record training completion |
| GET | `/operator/{id}/insights` | Operator Twin data |
| GET | `/ml-input/operator/{id}` | Unified AI/ML input payload |
| GET | `/weather` | Weather (always answers; synthetic fallback) |
| POST/GET | `/demo/start` · `/demo/stop` · `/demo/reset` · `/demo/status` | Replay control (below) |
| WS | `/ws` | Realtime events (below) |

### GET /health

```json
{"status": "ok", "database": "ok"}
```
`database`: `ok` | `not_configured` | `unavailable`. Always HTTP 200 while the API is up.

### GET /operators · GET /operators/{id}

Returns an operator object (or a list of them, ordered by `operator_id`). 404 if unknown.

```json
{"operator_id": "OP1001", "name": "Carlos Torres", "skill": "Intermediate", "base_speed": 1.012,
 "fatigue_start_hour": 14, "heat_sensitivity": 0.85, "rain_sensitivity": 0.284,
 "belt_skip_probability_when_idle": 0.65}
```

### GET /machines · GET /machines/{id}

```json
{"machine_id": "EXC001", "type": "excavator", "model": "CAT 320", "age_years": 2, "health_drift": 0.00028}
```

### GET /tasks/today

| Query | Required | |
| --- | --- | --- |
| `operator_id` | yes | e.g. `OP1001` |
| `date` | no | `YYYY-MM-DD`, overrides "today" |

Tasks ordered by `start_time`. For OP1001 the first one is **T001**.

```json
{"date": "2025-06-29", "operator_id": "OP1001",
 "tasks": [{"task_id": "T001", "task_type": "truck_loading", "zone": "A", "volume_m3": 160.0,
            "estimated_buckets": 107, "weather": "cloudy", "operator_id": "OP1001",
            "operator_skill": "Intermediate", "machine_id": "EXC001", "machine_age": 2,
            "estimated_time_min": 45.0, "actual_time_min": null,
            "start_time": "2025-06-29T07:30:00", "status": "scheduled"}, "..."]}
```
`status`: `completed` | `scheduled`. `actual_time_min` is null until completed.

### GET /tasks/{id}

A single task object (same shape as above). 404 if unknown.

### GET /telemetry/latest/{machine_id}

The machine's newest row. `source` is `live` while/after the replay has sent rows for the
machine (it advances row by row), otherwise `database` (e.g. after `/demo/reset`). 404 for an unknown machine or one with no telemetry.

```json
{"id": 25408, "timestamp": "2025-06-29T08:23:00", "machine_id": "EXC001", "operator_id": "OP1001",
 "task_id": "T001", "engine_hours": 3453.8, "fuel_used_l": 0.28, "load_cycles": 2,
 "avg_cycle_time_s": 27.3, "cycle_time_std": 3.24, "idling_time_min": 0.0, "idle_reason": null,
 "seatbelt_status": "fastened", "machine_moving": true, "harsh_events": 0,
 "lat": 40.693524, "lon": -89.588934, "safety_alert": null, "source": "database"}
```
Interval fields (`fuel_used_l`, `load_cycles`, `avg_cycle_time_s`, `idling_time_min`, …)
cover the period since the previous row. `id` is null for live rows.

### GET /telemetry/history/{machine_id}

| Query | Default | |
| --- | --- | --- |
| `limit` | 200 | most recent N rows (1–5000), returned **oldest first** |
| `task_id` | – | only rows for that task (`T001` → the 53-row replay script) |

```json
{"machine_id": "EXC001", "count": 3, "rows": [{"...telemetry row..."}]}
```

### GET /safety/{machine_id}

Evaluates the deterministic safety rules against the latest row plus the nearest worker.
While T001 replays it goes: `safe` → `unattended_machine` warning (07:56) → `seatbelt`
critical (07:57) → `safe` → `proximity` warning (08:12) → `proximity` critical (08:14) → `safe`.

```json
{"machine_id": "EXC001", "status": "critical", "timestamp": "2025-06-29T08:14:00",
 "operator_id": "OP1001", "task_id": "T001", "seatbelt_status": "fastened", "machine_moving": true,
 "idle_minutes": 0.0, "idle_reason": null,
 "nearest_worker": {"worker_id": "W04", "distance_m": 12.6, "direction": "right", "zone": "critical",
                    "timestamp": "2025-06-29T08:14:00"},
 "alerts": [{"type": "proximity", "severity": "critical", "message": "Worker 13 m from machine (right side)"}],
 "source": "live"}
```
- `status`: `safe` | `warning` | `critical` (worst alert). `alerts` is sorted most severe first.
- `idle_minutes` is continuous idle time, not the last interval.
- `nearest_worker.zone`: `critical` ≤15 m, `caution` ≤30 m, otherwise `safe`. `direction` is relative to the machine (`front|right|rear|left`). Null if there is no worker fix in the last 10 min.

Safety rules (`backend/app/services/safety_service.py`):

| `type` | Condition | Severity |
| --- | --- | --- |
| `seatbelt` | moving and seatbelt unfastened | critical |
| `proximity` | worker ≤15 m and machine moving | critical |
| `proximity` | worker ≤30 m (or ≤15 m while stationary) | warning |
| `unattended_machine` | unfastened, engine on, not moving, idle ≥8 min | warning |
| `avoidable_idle` | idle >5 min with `idle_reason = "avoidable"` | warning |

Truck waits (`idle_reason = "truck_wait"`) never trigger `avoidable_idle`.

### POST /incidents

Saves the incident together with a snapshot of recent telemetry (the "Black Box").

Request body:

| Field | Required | |
| --- | --- | --- |
| `description` | yes | 1–2000 chars |
| `task_id` | one of | fills operator + machine from the task |
| `operator_id` + `machine_id` | one of | both required if `task_id` is absent |
| `type` | no | default `manual_report` (e.g. `near_miss`, `harsh_event`) |
| `severity` | no | `info` \| `warning` (default) \| `critical` |
| `timestamp` | no | default: the machine's latest telemetry time |

Unknown fields are rejected (422). If `task_id` is omitted it is linked automatically
to the task the operator is running on that machine.

```json
{"operator_id": "OP1001", "machine_id": "EXC001", "type": "near_miss", "severity": "critical",
 "description": "Worker entered right-side swing zone"}
```

Response **201**:

```json
{"id": 14, "timestamp": "2025-06-29T08:23:00", "machine_id": "EXC001", "operator_id": "OP1001",
 "task_id": "T001", "type": "near_miss", "severity": "critical",
 "description": "Worker entered right-side swing zone", "source": "operator",
 "telemetry_snapshot": [{"...telemetry row, ISO timestamp..."}],
 "snapshot_source": "database", "snapshot_size": 5}
```
`snapshot_source`:
- `live_buffer`: the machine's rows received in the last ~60 s of live telemetry.
- `database`: when there is no live telemetry, the machine's last 5 stored rows up to the incident time.
- `none`: the machine has no telemetry at all.

### GET /incidents/{operator_id}

Newest first. Each item has the incident fields above plus `telemetry_snapshot`.

```json
{"operator_id": "OP1001", "count": 1, "incidents": [{"id": 14, "...": "..."}]}
```

### GET /training/recommendations/{operator_id}

Recommendations come from detected habits (see insights), plus training already
assigned but not completed. Triggers that already have a *completed* training are
not recommended again. Sorted with `high` priority (safety) first.

```json
{"operator_id": "OP1001",
 "recommendations": [
   {"clip_id": "CLIP_SEATBELT_01", "title": "Buckle up before you move", "trigger": "seatbelt",
    "reason": "Moved with seatbelt unfastened 45 times, usually right after a truck wait (fleet median 0).",
    "priority": "high", "status": "recommended", "metric_name": "seatbelt_violations",
    "current_metric": 45.0, "fleet_metric": 0.0},
   {"clip_id": "CLIP_FATIGUE_01", "title": "Managing afternoon fatigue", "trigger": "afternoon_slowdown",
    "reason": "Cycles are 24% slower after 15:00 than before noon (fleet 1%).", "priority": "medium",
    "status": "recommended", "metric_name": "afternoon_pace_ratio", "current_metric": 1.243,
    "fleet_metric": 1.013}],
 "completed": []}
```
`status`: `recommended` | `assigned`. Clip catalog:

| clip_id | trigger | metric |
| --- | --- | --- |
| `CLIP_SEATBELT_01` | seatbelt | seatbelt_violations |
| `CLIP_IDLE_01` | avoidable_idle | avoidable_idle_min_per_hour |
| `CLIP_SMOOTH_01` | harsh_events | harsh_events_per_hour |
| `CLIP_FATIGUE_01` | afternoon_slowdown | afternoon_pace_ratio |
| `CLIP_FUEL_01` | fuel_inefficiency | fuel_vs_fleet_ratio |

### POST /training/complete

```json
{"operator_id": "OP1001", "clip_id": "CLIP_SEATBELT_01"}
```
Optional: `timestamp`, `before_metric`, `after_metric`.
- `before_metric` is chosen in this order: the value in the request, then the value stored when the training was assigned, then the operator's current value for the clip's metric.
- `after_metric` stays null until measured later.

If an assigned, incomplete training exists for the clip, it is marked complete
(`created: false`). Otherwise a new completed event is created.

```json
{"training_event": {"id": 5, "operator_id": "OP1001", "trigger": "seatbelt", "clip_id": "CLIP_SEATBELT_01",
                    "timestamp": "2025-06-29T08:23:00", "completed": true,
                    "metric_name": "seatbelt_violations", "before_metric": 45.0, "after_metric": null},
 "created": true}
```
Unknown `clip_id` → 422 `invalid_request`. Unknown operator → 404.

### GET /operator/{id}/insights

Deterministic Operator Twin data. It is computed from history **before today**, so the scripted demo telemetry never leaks in.

```json
{"operator": {"...operator..."},
 "history_until": "2025-06-29T00:00:00",
 "summary": {"tasks_completed": 227, "operating_hours": 222.1, "avg_actual_vs_estimate": 1.11,
             "avg_eta_error_min": 6.3, "fuel_per_cycle_l": 0.1423, "fuel_vs_fleet_ratio": 0.978,
             "avoidable_idle_min_per_hour": 3.76, "legitimate_idle_min_per_hour": 5.931,
             "harsh_events_per_hour": 0.122, "seatbelt_violations": 45, "unbelted_idle_samples": 125,
             "afternoon_pace_ratio": 1.243},
 "fleet": {"...fleet medians of the same keys..."},
 "pace_by_hour": [{"hour": 7, "avg_cycle_time_s": 25.47, "pace_index": 0.939, "samples": 133}, "..."],
 "machines": [{"machine_id": "EXC001", "tasks": 17, "fuel_per_cycle_l": 0.1213, "fleet_fuel_per_cycle_l": 0.1151}, "..."],
 "safety": {"alerts": {"seatbelt": 45, "unattended_machine": 16, "avoidable_idle": 54},
            "near_misses": 2, "incidents": 0},
 "habits": [{"habit_type": "seatbelt", "count": 45, "severity": "critical",
             "explanation": "Moved with seatbelt unfastened 45 times, usually right after a truck wait (fleet median 0).",
             "metric_name": "seatbelt_violations", "metric": 45.0, "fleet_metric": 0.0}, "..."],
 "training": [{"...training event..."}]}
```
- `fuel_vs_fleet_ratio`: fuel ÷ what the fleet burns for the same buckets on the same machines. 1.0 = average; this separates operator effects from machine wear.
- `afternoon_pace_ratio`: cycle time after 15:00 ÷ before 12:00, normalised per machine.
- `pace_index`: >1 means slower than the machine's fleet average.
- `legitimate_idle_min_per_hour`: truck waits. This is **not** the operator's fault.

Habit rules (`habit_type`):

| habit_type | Rule |
| --- | --- |
| `seatbelt` | ≥3 seatbelt alerts |
| `avoidable_idle` | rate > 1.5× fleet median |
| `harsh_events` | rate > 2× fleet median |
| `afternoon_slowdown` | `afternoon_pace_ratio` ≥ 1.10 |
| `fuel_inefficiency` | `fuel_vs_fleet_ratio` ≥ 1.2× the median of same-skill operators |

### GET /ml-input/operator/{id}

One payload so the AI/ML layer never queries the database.

| Query | Default | |
| --- | --- | --- |
| `task_id` | operator's current task today (first not completed) | must belong to the operator (else 422) |
| `as_of` | live replay time for that task, else the task's `start_time` | nothing after this time is included |

```json
{"operator": {"...operator..."},
 "machine": {"...machine..."},
 "task": {"...task (T001 for OP1001)..."},
 "recentTelemetry": ["up to 30 telemetry rows of the operator at or before asOf, oldest first"],
 "weather": {"timestamp": "2025-06-29T08:00:00", "condition": "rain", "temperature": 16.0,
             "rain_mm": 2.8, "wind_speed": 18.0, "source": "synthetic"},
 "history": [{"...task fields...", "avg_cycle_time_s": 33.33, "fuel_used_l": 33.86, "load_cycles": 161,
              "avoidable_idle_min": 0.0, "truck_wait_idle_min": 0.0, "harsh_events": 0,
              "seatbelt_alerts": 0, "temperature": 30.9, "rain_mm": 0.0, "wind_speed": 11.5}],
 "asOf": "2025-06-29T08:05:00"}
```
`history` = all of the operator's completed tasks before today (and before `asOf`),
oldest first, with per-task telemetry aggregates and weather at task start. It is
ready-made training data for the ETA model. The example above used `?as_of=2025-06-29T08:05:00`.

### GET /weather

| Query | Default |
| --- | --- |
| `at` | time of the latest telemetry row |

```json
{"timestamp": "2025-06-29T09:00:00", "condition": "heavy_rain", "temperature": 15.5,
 "rain_mm": 5.6, "wind_speed": 24.0, "source": "synthetic"}
```
`source`:
- `synthetic`: the seeded demo weather, or a fixed formula if the DB is down.
- `live`: from `WEATHER_MODE=live` + `WEATHER_API_URL`.
- `fallback`: live mode was on but the external call failed.

This endpoint never fails because of the weather provider.

---

## Demo replay control

The shared demo replays the stored telemetry of **T001** (OP1001 on EXC001) from
PostgreSQL, one row every `REPLAY_INTERVAL_SECONDS` (default 3 s; 53 rows ≈ 2.6 min).

| Method | Path | Purpose |
| --- | --- | --- |
| POST | `/demo/start?interval=` | Start the replay. `interval` (0–60 s) overrides the env default. A start while running is a no-op (`"started": false`); there is never a second loop. |
| POST | `/demo/stop` | Stop immediately. Live state (latest row, 60 s buffer) is kept. |
| POST | `/demo/reset` | Stop and clear EXC001's live state (`/telemetry/latest` falls back to the DB). |
| GET | `/demo/status` | Replay status + number of connected WebSocket clients. |

```json
{"started": true, "message": "Replay started", "clients": 1,
 "status": {"state": "running", "taskId": "T001", "operatorId": "OP1001", "machineId": "EXC001",
            "rowsSent": 0, "totalRows": null, "intervalSeconds": 3.0, "lastTimestamp": null, "error": null}}
```
`state`: `idle` | `running` | `finished` | `stopped` | `error`. Every start replays from the first row,
so runs are identical. The replay feeds the same live store the REST API reads, so
during a replay `GET /telemetry/latest/EXC001` returns `source: "live"` and advances row by
row, `GET /safety/EXC001` shows the live state, and `POST /incidents` snapshots the live 60 s buffer
(`snapshot_source: "live_buffer"`) without interrupting the replay.

CLI (prints events live): `python -m simulator.replay [--interval 1] [--quiet]`.

## WebSocket: `WS /ws`

URL: `ws://localhost:8000/ws` (frontend: `NEXT_PUBLIC_WS_URL`). Server → client JSON messages:

```json
{"event": "telemetry_update", "version": 1, "data": {...}}
```

`event` names and `data` keys are stable. Every `data` also carries
`machineId`/`operatorId`/`taskId` where they apply, and `timestamp` (the
telemetry time the event belongs to, ISO). On connect the client receives a
`replay_status`. Clients may send `{"action": "ping"}` (→ `pong`) or
`{"action": "status"}` (→ `replay_status`); anything else → `error`, and the connection stays open.

| event | data (handover keys **bold**) | When |
| --- | --- | --- |
| `telemetry_update` | **timestamp, cycleTime, idle, fuel, belt, movement** | every replayed row |
| `safety_alert` | **severity, type, message** | a rule becomes active (`seatbelt` critical, `unattended_machine` / `avoidable_idle` warning), once per activation |
| `proximity_alert` | **severity, distance, direction**, zone, workerId | nearest worker's level changes. `severity`: `warning` \| `critical` \| `safe` (= all clear). `zone`: `safe` \| `caution` \| `critical` (50/30/15 m bands). Critical only while the machine moves |
| `eta_update` | **min, max, original, reason, bucketsRemaining** | at start (plan) and when min/max moves ≥2 min or the reason changes |
| `habit_detected` | **habitType, count, explanation** | first live occurrence of a behaviour the operator already has as a habit |
| `training_recommendation` | **clipId, title, reason** | right after `habit_detected` (stored recommendation; catalog clip if already trained) |
| `replay_status` | state, taskId, operatorId, machineId, rowsSent, totalRows, intervalSeconds, lastTimestamp, error | on connect, start, finish/stop/reset/error |
| `error` / `pong` | message / – | replies to client messages |

Per row the order is: `telemetry_update` → `safety_alert` → `proximity_alert` → `eta_update`
→ `habit_detected` → `training_recommendation`.

### What the T001 demo emits (observed, every run identical)

| Telemetry time | Event |
| --- | --- |
| 07:30 | `eta_update` 45–45 "Plan estimate" |
| 07:31 → 08:23 | 53 × `telemetry_update` |
| 07:53–07:58 | `eta_update` 45→49–52 "N min of waiting so far" (truck wait) |
| 07:56 | `safety_alert` warning `unattended_machine` (belt off, idle 8 min) |
| 07:57 | `safety_alert` critical `seatbelt` → `habit_detected` seatbelt (count 46) → `training_recommendation` CLIP_SEATBELT_01 |
| 08:02–08:03 | `eta_update` 51–54 → **53–56** "Rain (2.8 mm/h) slowed cycles from 22.6 s to 28.1 s; …" |
| 08:12 | `proximity_alert` warning, W04 29.2 m right |
| 08:14 | `proximity_alert` **critical**, W04 12.6 m right |
| 08:15 / 08:17 | `proximity_alert` warning 21.2 m / safe 46 m |
| 08:23 | `eta_update` 53–53 "Task complete", then `replay_status` finished |

Example messages:

```json
{"event": "telemetry_update", "version": 1, "data": {"machineId": "EXC001", "operatorId": "OP1001", "taskId": "T001",
  "timestamp": "2025-06-29T07:57:00", "cycleTime": 22.1, "idle": 0.0, "fuel": 0.28, "belt": "unfastened", "movement": true}}
{"event": "safety_alert", "version": 1, "data": {"machineId": "EXC001", "operatorId": "OP1001", "taskId": "T001",
  "timestamp": "2025-06-29T07:57:00", "severity": "critical", "type": "seatbelt", "message": "Machine moving with seatbelt unfastened"}}
{"event": "proximity_alert", "version": 1, "data": {"machineId": "EXC001", "timestamp": "2025-06-29T08:14:00", "workerId": "W04",
  "severity": "critical", "zone": "critical", "distance": 12.6, "direction": "right"}}
{"event": "eta_update", "version": 1, "data": {"taskId": "T001", "timestamp": "2025-06-29T08:03:00", "min": 53, "max": 56,
  "original": 45, "reason": "Rain (2.8 mm/h) slowed cycles from 22.6 s to 28.1 s; 8 min of waiting so far", "bucketsRemaining": 42}}
{"event": "habit_detected", "version": 1, "data": {"operatorId": "OP1001", "timestamp": "2025-06-29T07:57:00", "habitType": "seatbelt",
  "count": 46, "explanation": "Moved with seatbelt unfastened 45 times, usually right after a truck wait (fleet median 0). Seen again today at 07:57."}}
{"event": "training_recommendation", "version": 1, "data": {"operatorId": "OP1001", "timestamp": "2025-06-29T07:57:00",
  "clipId": "CLIP_SEATBELT_01", "title": "Buckle up before you move", "reason": "Moved with seatbelt unfastened 45 times, usually right after a truck wait (fleet median 0)."}}
```

### ETA (deterministic fallback until the ML model exists)

`backend/app/services/eta_service.py`: from the rows replayed so far,
`min = elapsed + bucketsRemaining × recent cycle time` and `max = the same with the plan's
15 % allowance for waits`. Before 3 working samples it returns the plan (45 min for T001).
The ML model can replace `estimate_eta()` without changing this event.

Frontend minimal client:

```js
const ws = new WebSocket(process.env.NEXT_PUBLIC_WS_URL); // ws://localhost:8000/ws
ws.onmessage = (e) => { const { event, data } = JSON.parse(e.data); /* switch (event) ... */ };
await fetch(`${API}/demo/start`, { method: "POST" });
```
