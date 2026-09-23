# ML → Backend Integration Guide

This is the one document the backend developer needs to read to call the
entire ML layer — everything else in `ml/` (README, module docstrings) is
reference material for the ML developer, not a prerequisite for integration.

## 1. How the backend loads ML

The ML layer is a plain Python package (`ml/src/`) with no server of its
own — the backend imports it directly (same Python environment, or a small
FastAPI wrapper around the entry point below). There is no network call.

```python
import sys
sys.path.insert(0, "<repo_root>/ml")  # or install ml/ as an editable package

from src.intelligence.operator_state import generate_operator_state
from src.intelligence.realtime import update_operator_state
```

**Prerequisite — train the ETA model once**, before the first call:

```bash
cd ml
python -m venv .venv && source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python run_pipeline.py            # generates data/synthetic/ + data/ground_truth/
python run_eta_pipeline.py --train  # writes ml/models/eta/model.joblib + metadata.json
```

`ml/models/` is git-ignored (same policy as `data/processed/`) — this is a
one-time local step, not something CI/deploy needs to repeat on every
startup. `generate_operator_state()` loads the saved model from disk once
and caches it in-process (`src.eta.model_io.load_eta_model()`); nothing is
retrained by calling it.

## 2. Main entry point

```python
state = generate_operator_state(operator_id, machine_id, task_id, current_context=None, tables=None, features_df=None)
```

- `operator_id`, `machine_id`, `task_id`: strings, e.g. `"OP1001"`, `"EXC001"`, `"T001"`. Must be **mutually consistent** — `machine_id`/`operator_id` must match `task_id`'s actual recorded machine/operator in `tasks.csv`, or the call raises `ValueError` (a mismatch would otherwise silently produce a state where the ETA is computed for the task's real machine but the diagnosis/briefing sections are filtered to a different one).
- `current_context` (optional dict):
  - `as_of` (`pandas.Timestamp`): point in time to evaluate Focus Battery at. Defaults to the task's own `start_time`.
  - `telemetry_so_far` (`pandas.DataFrame`): telemetry recorded for this task so far, same shape as the `telemetry` table. **Omit this (or pass `None`) for a task that hasn't started yet** — the default is an empty window, not "everything recorded up to now" (a subtle but important distinction; see the code comment in `operator_state.py` if curious why).
- `tables` / `features_df` (optional, performance): see §7's timing table — pass these back in on repeat calls (e.g. a fleet dashboard listing several operators) to skip a multi-second data-load-and-feature-rebuild. Both are handed back in the returned state's `_context` for exactly this purpose:
  ```python
  first = generate_operator_state("OP1001", "EXC001", "T001")
  second = generate_operator_state(
      "OP1011", "EXC004", "T500",
      tables=first["_context"]["tables"],
      features_df=first["_context"]["features_df"],
  )  # ~15x faster than a cold call
  ```

Raises `ValueError` for an unknown `operator_id`, `machine_id`, or `task_id`, or for a `machine_id`/`operator_id` that doesn't match `task_id`'s real assignment.

## 3. Input JSON schema

If the backend calls this from an HTTP handler, the request body maps
directly onto the function arguments:

```json
{
  "operator_id": "OP1001",
  "machine_id": "EXC001",
  "task_id": "T001",
  "current_context": {
    "as_of": "2026-06-01T09:15:00",
    "telemetry_so_far": [
      {"timestamp": "2026-06-01T07:00:00", "machine_moving": true, "seatbelt_status": "buckled", "...": "..."}
    ]
  }
}
```

`current_context` and everything inside it is optional — an empty/omitted
body is a valid, safe call (returns the pre-task state).

## 4. Output JSON schema

```json
{
  "operator_id": "OP1001",
  "machine_id": "EXC001",
  "task_id": "T001",
  "operator_twin": {"operatorId": "...", "paceFactor": 1.13, "rainSensitivity": 0.07, "heatSensitivity": 0.02, "afternoonEffect": -0.13, "fuelEfficiency": 1.02, "seatbeltViolationRate": 0.002, "nTasks": 165},
  "eta": {"eta_min": 14.3, "eta_max": 33.4, "eta_point": 22.9, "original_eta": 32.5, "reason": "...", "factors": [...], "buckets_remaining": 65, "model_name": "linear_regression"},
  "dynamic_eta": {"eta_min": "...", "eta_max": "...", "eta_point": "...", "pct_complete": 0.0, "cycle_time_change_pct": null, "reason": "..."},
  "remaining_work": {"total_buckets": 65, "buckets_completed": 0, "buckets_remaining": 65, "pct_complete": 0.0, "trucks_remaining": null},
  "risk": {"risk_level": "low", "score": 10, "factors": [], "explanation": "...", "hard_rule_triggered": null},
  "habits": [{"operator_id": "OP1001", "habit_type": "seatbelt_during_truck_wait", "count": 3, "opportunities": 58, "frequency": 0.052, "z_score": -0.6, "is_habit": false, "explanation": "..."}],
  "idle_analysis": {"task_id": "T001", "legitimate_idle_min": 0.0, "avoidable_idle_min": 5.0, "total_idle_min": 5.0, "dominant_idle_type": "avoidable"},
  "focus": {"operator_id": "OP1001", "score": 100, "factors": [], "disclaimer": "Operational workload indicator only — not a medical or clinical fatigue measurement.", "recommendation": "..."},
  "fuel_diagnosis": [{"source": "operator", "operator_id": "OP1010", "evidence": "...", "ratio_vs_fleet": 1.31, "n_distinct_entities": 8}],
  "training": {"recommended": true, "clip_id": "TR_SWING_ZONE", "title": "...", "reason": "...", "duration_seconds": 50, "safe_timing": "post_task", "trigger_type": "proximity_event"},
  "threat_briefing": [{"priority": 1, "risk": "...", "reason": "...", "source": "safety"}],
  "explanations": {"eta": {"reason": "...", "factors": [...]}, "operator_twin": {"...": "..."}, "...": "..."},
  "_context": { "// internal — see section 5, strip before sending to the frontend": "" }
}
```

Notes:
- `habits` is a list (currently always length 1 — one summary for the
  requested operator) to leave room for multiple habit types later without
  a breaking schema change.
- `fuel_diagnosis` is a list, filtered to findings that mention this
  operator or this machine — usually 0 or 1 items, occasionally 2 if both
  happen to be flagged.
- `training.recommended: false` results omit `clip_id`/`title`/etc. — check
  `recommended` before reading the rest.
- `threat_briefing` is `[]` when nothing meaningful was found — that IS the
  answer, not a missing/failed computation.
- **`_context` is internal** (feeds `update_operator_state()`, see below) —
  it holds live pandas DataFrames and a loaded model object, is not
  JSON-serializable as-is, and should never be sent to the frontend. If
  exposing this over HTTP, strip `_context` from the response and instead
  keep the full Python `state` dict server-side (e.g. cached by
  `task_id`) for the next realtime update call.

## 5. Real-time update function

```python
new_state = update_operator_state(previous_state, new_telemetry, weather_row=None, task_context=None)
```

- `previous_state`: the full dict `generate_operator_state()` (or a prior
  `update_operator_state()` call) returned — **must include `_context`**,
  so keep the Python object, not a re-serialized copy of the JSON response.
- `new_telemetry`: one telemetry row as a dict (same fields as the
  `telemetry` table: `timestamp`, `machine_moving`, `seatbelt_status`,
  `safety_alert`, `load_cycles`, `idle_reason`, `avg_cycle_time_s`, ...).
- `weather_row` (optional): `{"condition": "rain"}` to override the
  weather-driven risk factor for this tick.
- `task_context` (optional): `{"nearest_worker_distance_m": 4.2}` for a
  live proximity reading.

Returns a new state dict with `dynamic_eta`, `remaining_work`, `risk`,
`habits`, `focus`, `training`, and the matching `explanations` entries
updated; everything else (the Twin, the baseline `eta`, `idle_analysis`,
`threat_briefing`) is carried forward unchanged from `previous_state` —
those don't change from one telemetry tick.

**This never retrains or reloads a model.** The ETA model bundle and every
loaded table are reused from `previous_state["_context"]`; the only
per-call work is a few small pandas operations on that operator's own task
slice. See `ml/tests/test_realtime.py::test_no_model_retraining_uses_cached_bundle`.

## 6. Error handling

| Situation | Behavior |
|---|---|
| Unknown `task_id` | `generate_operator_state()` raises `ValueError` |
| ETA model not trained yet | `load_eta_model()` (called internally) raises `FileNotFoundError` with the exact command to fix it |
| `update_operator_state()` called with a state missing `_context` | raises `ValueError` — usually means a JSON round-trip stripped it; keep the Python object |
| A task with no synthetic telemetry yet | Returns a valid state with `remaining_work.buckets_remaining == total_buckets` and an empty `idle_analysis`/near-miss set — not an error |

The backend should catch `ValueError`/`FileNotFoundError` around these
calls and return a 4xx/5xx as appropriate — the ML layer does not swallow
these itself, per the project's "never silently fabricate results" rule.

## 7. Model loading

- `src.eta.model_io.load_eta_model()` is the only model-loading path. It
  reads `ml/models/eta/model.joblib` + `metadata.json`, and caches the
  result in a module-level variable — call it as often as you like, disk is
  only touched once per process (or once per `force_reload=True` call).
- No other subsystem here (Habit Radar, Idle Shield, Focus Battery, Risk,
  Diagnosis, Training) has a trained model to load — they're all
  deterministic rules/statistics computed directly from the tables at call
  time.

### Measured performance (production-readiness audit, full ~2,800-task dataset)

| Call | Time | Notes |
|---|---|---|
| `load_eta_model()` — first call | ~1.3s | One-time cost (first `sklearn` import + disk read); cached after that, effectively 0ms on repeat calls. |
| `predict_eta()` (single point prediction) | ~2ms | |
| `generate_operator_state()` — cold (nothing cached) | ~1.7s | Dominated by the one-time model load above. |
| `generate_operator_state()` — repeat call, `tables`/`features_df` reused | **~270ms** | See §2 — pass these back in for a fleet view / repeated calls in one session. |
| `update_operator_state()` (one realtime telemetry tick) | **~15ms** | The realtime path — never retrains, never reloads data. Safe for a live demo. |

A real bug found during the audit: the pre-fix `generate_operator_state()`
took **~4.4 seconds per call, even on a second call with nothing changed**,
because a Habit Radar internal helper used a per-task Python loop over the
full telemetry table (~2s of that alone). It's now vectorized (~30ms for
the same computation) — see the "Behaviour + Safety Intelligence subsystem"
section of `ml/README.md` and `tests/test_habit_radar.py`'s performance
regression test.

## 8. Example: OP1001 / EXC001 / T001

```bash
cd ml
python run_intelligence_pipeline.py
```

prints the full state (every section below) plus a short realtime-update
demonstration. Equivalent Python:

```python
from src.intelligence.operator_state import generate_operator_state
from src.intelligence.realtime import update_operator_state

state = generate_operator_state("OP1001", "EXC001", "T001")
print(state["eta"])
print(state["risk"])
print(state["threat_briefing"])

# Later, as telemetry arrives:
new_state = update_operator_state(state, {
    "timestamp": "2026-06-01T07:05:00",
    "machine_moving": True,
    "seatbelt_status": "buckled",
    "safety_alert": False,
    "load_cycles": 2,
    "idle_reason": None,
})
print(new_state["dynamic_eta"])
```
