# OpAssure — AI/ML

**Owner:** AI/ML developer
**Stack:** Python, pandas, numpy, scikit-learn

> **Status:** the ML layer is complete and integration-ready. Data foundation,
> ETA / Operator Twin, Behaviour + Safety Intelligence (Habit Radar, Idle
> Shield, Focus Battery, risk intelligence, machine-vs-operator diagnosis),
> and the final intelligence layer (Just-in-Time Micro Training, training
> effectiveness, instructor escalation, Pre-Task Threat Briefing, structured
> explanations, and the unified `generate_operator_state()` / `update_operator_state()`
> entry points) are all built and tested — see `ml/docs/integration.md` for
> the backend handoff. See `CLAUDE.md` §11 for ML principles and §8 for the
> priority system.

## What this is

This package turns raw operator/machine/task/telemetry data into a single
ML-ready, task-level feature matrix that ETA, Operator Twin, and anomaly
detection can all train against — using the **same feature definitions**, so
the three models never quietly disagree about what a column means.

Since the backend's own telemetry simulator (`backend/simulator/`) isn't
implemented yet, this package also includes a **deterministic synthetic data
generator** as a fallback. It is not meant to be a realistic physics
simulation — it exists to produce a dataset that is just realistic enough to
exercise every downstream feature, with the six planted patterns from
`CLAUDE.md` §6 present and labeled so detection can be evaluated.

## Input datasets

Generated into `data/synthetic/` (20 operators, 8 machines, 60 days — see
`src/common/config.py` to change the scale):

| Table | What it is |
|---|---|
| `operators.csv` | Static per-operator profile (skill, base speed, fatigue hour, weather sensitivities, seatbelt-skip probability). |
| `machines.csv` | Static per-machine profile (type, age, health drift rate). |
| `weather.csv` | Hourly weather for the whole simulation window. |
| `tasks.csv` | One row per task: type, zone, volume, assigned operator/machine, planner's `estimated_time_min`, and the simulated `actual_time_min`. |
| `telemetry.csv` | ~5-minute interval readings per task: fuel, cycles, idle time/reason, seatbelt status, position, safety alerts. |
| `worker_positions.csv` | Periodic site-worker position samples. |
| `near_misses.csv` | Worker positions that fell inside a machine's swing-zone radius while it was moving. |
| `incidents.csv` | A subset of safety alerts / near-misses that got "reported" as incidents. |
| `training_events.csv` | Just-in-time training events triggered for the seatbelt-habit operator. |

Ground truth, in `data/ground_truth/`:

| Table | What it is |
|---|---|
| `ground_truth_labels.csv` | One row per planted pattern (entity-level: which operator/machine/task-type it applies to, and why). |
| `task_ground_truth.csv` | One row **per task** with a boolean flag for each planted pattern — the table `/ml-evaluation` and `/data-validation` actually check detections against. |

The six planted patterns (see `CLAUDE.md` §6 for the full description):
seatbelt habit (`OP1005`), afternoon slowdown (all operators, worse with
heat), machine degradation (`EXC002`), operator inefficiency (`OP1010`),
legitimate idle (truck-dependent task types), and proximity near-misses.

Deterministic demo identifiers (`OP1001` / `EXC001` / `T001`, per `CLAUDE.md`
§7) are guaranteed to exist — day 0's first task on `EXC001` is forced to
`T001` / `OP1001`.

## Feature pipeline

```
src/common/          paths, seeds, scale constants, CSV I/O, time/geo helpers, loaders, the generator
src/features/        per-source feature builders + the shared orchestrator (build_features.py)
src/eta/              build_eta_dataset()          -> target: actual_time_min
src/operator_twin/    build_operator_twin_dataset() -> target: actual - planner-estimated time (personalization gap)
src/anomaly/          build_anomaly_dataset()       -> targets: the task_ground_truth.csv boolean columns
src/safety/, src/training/   not implemented yet (will reuse the same pipeline)
src/evaluation/       time_aware_split() — chronological train/val/test split
```

All three `dataset.py` modules call the same
`src.features.build_features.build_task_level_dataset()` — that's what
`feature_columns()` in that module returns as the safe-to-train-on column
list. Concretely, each task-level row combines:

- **Static features**: operator profile, machine profile, task attributes
  (one-hot task type/zone), weather at task start (as-of merged — never a
  future reading).
- **Time-aware historical features** (`src/features/telemetry_features.py`):
  each operator's and machine's expanding-average past performance, and a
  machine's "recent 5 tasks vs. all-time average" gap — computed using
  **only tasks that started strictly before the current one**. This is what
  lets a model pick up on machine degradation or operator inefficiency
  without ever being told which machine/operator was planted as anomalous,
  and without leaking the row's own outcome into its own features.

`actual_time_min` is kept as the label column and explicitly excluded from
`feature_columns()` (see `LEAKAGE_COLUMNS`) so it can never accidentally be
used as a model input.

## Output datasets

`ml/run_pipeline.py` builds the ETA feature matrix and saves it to
`data/processed/task_features.csv` (2,822 rows × 55 columns from the current
seed — 20 operators × 8 machines × 60 days). `data/processed/` contents are
git-ignored (see the root `.gitignore`) since they're a reproducible build
artifact — regenerate them any time with the command below.

## ETA + Operator Twin subsystem

```
src/eta/
  train.py           trains + compares candidate models, selects the best, saves the artifact
  model_io.py         load_eta_model() — loads the saved artifact, cached in-process
  dataset.py           build_eta_dataset() (from the foundation step)
  inference.py         predict_eta(), predict_personalized_eta()
  dynamic.py            predict_dynamic_eta() — in-progress ETA updates
  remaining_work.py    calculate_remaining_work()
  explain.py            build_eta_explanation() — structured, rule-based ETA reasons

src/operator_twin/
  twin.py             build_operator_twin(), get_operator_profile()
  dataset.py           build_operator_twin_dataset() (from the foundation step)
```

### Models created

Two candidates are trained on the **train** split and compared on the **val**
split (never a random shuffle — reuses `src.evaluation.splits.time_aware_split`
as-is):

| Candidate | Why it's here |
|---|---|
| `linear_regression` | Fast, interpretable baseline — "can we beat a straight line". |
| `random_forest` | Captures non-linear weather/fatigue/degradation interactions without tuning. |

The lower-validation-MAE candidate is selected automatically (currently
`linear_regression` on this dataset) and saved to `ml/models/eta/model.joblib`,
with `ml/models/eta/metadata.json` holding the feature column list, both
candidates' metrics (val for both, test for the winner only), and the
residual-quantile interval offsets. **Model artifacts are git-ignored** (same
policy as `data/processed/`) — run the training command below once locally.

### Personalized ETA — uncertainty approach

`predict_personalized_eta()` returns an interval, not a fake single point:
the model's point prediction plus the **empirical 10th/90th-percentile
residuals from the validation set** (`config.ETA_RESIDUAL_QUANTILES`).
Simple, defensible, and re-computed every time the model is retrained — no
separate quantile-regression model needed.

### Operator Twin — estimates and shrinkage

`build_operator_twin()` computes, per operator, from their own task/telemetry
history (never from the generator's hidden ground-truth parameters):

| Field | Convention |
|---|---|
| `pace_factor` | Speed multiplier vs. fleet average. `>1` = faster, `<1` = slower. |
| `rain_sensitivity` / `heat_sensitivity` | Non-negative — how much slower they get in rain/heat. |
| `afternoon_effect` | `<0` = measurably slower in the afternoon (matches the planted pattern being unfavorable). |
| `fuel_efficiency` | `>1` = uses less fuel than fleet average. |
| `seatbelt_violation_rate` | Fraction of moving telemetry intervals with the seatbelt unbuckled. |

Operators with little history are **shrunk toward the fleet average**
(`n / (n + k)` weighting, `k = config.OPERATOR_TWIN_SHRINKAGE_K`) rather than
overfitting to 1-2 noisy tasks. Pass `as_of=<timestamp>` to compute the twin
using only tasks before that point — this is what `predict_dynamic_eta` would
use in a leakage-safe setting, versus the default full-history snapshot used
for a dashboard/demo.

### Dynamic ETA

`predict_dynamic_eta()` is deliberately **rule-based, not a second model** —
it takes the elapsed time, the recent cycle time from telemetry vs. the pace
implied by the original prediction, and the remaining buckets
(`calculate_remaining_work()`), and recomputes the estimate. The interval
width shrinks as the task nears completion. `trucks_remaining` is always
`None` — the data model has no bucket-per-truck capacity field, and inventing
one would be exactly the kind of fabricated number the project forbids.

### Explanations

`build_eta_explanation()` returns `{"reason": str, "factors": [...]}` with
each factor tied to a measurable input (weather, operator pace, machine age,
observed cycle-time change vs. plan, afternoon fatigue) — no LLM involved.

## Behaviour + Safety Intelligence subsystem

```
src/anomaly/
  habit_radar.py       detect_habits(), get_habit_summary()
  idle_shield.py        classify_idle(), classify_task_idle()
  diagnosis.py           diagnose_fuel_source()

src/safety/
  focus_battery.py      calculate_focus(), get_focus_recommendation()
  risk.py                 calculate_risk(), get_risk_factors()

src/evaluation/
  behaviour_eval.py     evaluate_habit_radar(), evaluate_idle_shield(),
                          evaluate_diagnosis(), evaluate_seatbelt_critical_detection(),
                          evaluate_all()
```

All of these consume the existing loaders/feature pipeline/Operator Twin
as-is — no second feature-engineering pipeline was created.

### Habit Radar

Detects the planted **seatbelt-during-truck-wait** pattern: seatbelt removed
during an idle wait, still unfastened the moment the machine starts moving
again. A task's telemetry has at most one contiguous idle block, so a
task-level idle→moving transition after a `waiting_for_truck` idle reason is
exactly one *opportunity*; a deterministic per-task scan finds these without
needing general sequence-mining (PrefixSpan etc.) for this single fixed
pattern.

**A single event is never a habit.** `detect_habits()` requires all of:
`opportunities >= HABIT_MIN_OPPORTUNITIES` (3), `count >= HABIT_MIN_COUNT`
(2), **and** the operator's frequency being a statistical outlier vs. the
rest of the fleet (`z_score >= HABIT_Z_THRESHOLD`, default 2.0). The z-score
bar is relative, not a fixed absolute rate — the generator re-samples the
seatbelt state every 5 minutes during an idle block rather than once per
idle period, so even a low-probability operator can occasionally rack up a
non-trivial raw frequency; what distinguishes a genuine habit is standing
out from peers, not clearing an arbitrary number.

### Idle Shield

`classify_idle()` reads the telemetry's own `idle_reason` field (a real,
legitimately-available column — not a hidden generator secret) and returns
`{"idle_type": "legitimate"|"avoidable", "reason": str, "confidence": float}`.

**Hard, unconditional no-blame rule:** any idle reason in
`config.LEGITIMATE_IDLE_REASONS` (`waiting_for_truck`, `waiting_for_instruction`,
`break`) is *always* `"legitimate"` — this is never a learned weight that
could get overridden. `classify_task_idle()` aggregates a task's idle
minutes into a dominant type for task-level evaluation.

### Focus Battery

`calculate_focus()` returns a deterministic 0-100 **operational workload
indicator** — explicitly not a medical/clinical fatigue measurement (see the
`disclaimer` field on every result). It's built from continuous work hours,
time of day, heat (weighted by the operator's own `heatSensitivity` from
their Twin), historical afternoon slowdown (`afternoonEffect` from the
Twin), recent cycle-time deterioration, and repetitive task count.
`get_focus_recommendation()` adds a break suggestion when the score is low.

### Risk intelligence

`calculate_risk()` is a contextual layer **on top of** two hard,
non-negotiable safety rules that no score can downgrade:

1. machine moving + seatbelt unfastened → always `"critical"`
2. a worker inside the swing-zone radius while the machine is moving →
   always `"critical"`

Only when neither hard rule fires does it compute a contextual 0-100 score
from softer signals (recent safety alerts, a detected Habit Radar pattern,
weather, machine degradation, "somewhat close" proximity) into
low/medium/high. Every result carries `hard_rule_triggered` so callers (and
tests) can verify which path produced it.

### Machine vs. operator fuel diagnosis

`diagnose_fuel_source()` distinguishes a machine burning extra fuel for
everyone who runs it from an operator burning extra fuel on every machine
they run — each requires evidence across `>= DIAGNOSIS_MIN_DISTINCT_ENTITIES`
(3) of the other entity type at `>= DIAGNOSIS_ELEVATED_RATIO` (15%) above
the fleet average, with the elevation showing up for most (not just one) of
those entities.

### Evaluating against ground truth

`run_behaviour_pipeline.py` prints the full evaluation report. Summary from
the current generated dataset:

| Check | Result |
|---|---|
| Habit Radar flags exactly `OP1005` | precision/recall/F1 = 1.0/1.0/1.0, 0 false positives |
| Idle Shield legitimate-idle falsely blamed on operator | **0 / 1126 truck-wait tasks (0.0%)** — the critical no-blame guarantee |
| Idle Shield task-level accuracy vs. `task_ground_truth` | 47% (see note below — not a `classify_idle()` defect) |
| Diagnosis flags `EXC002` (machine) and `OP1010` (operator) | both correctly flagged, 0 false positives |
| Hard critical-risk rule vs. telemetry's own `safety_alert` | precision/recall = 1.0/1.0 (sanity check — should be ~perfect by construction) |

**Why Idle Shield's task-level accuracy is only ~47%, honestly explained:**
`classify_idle()` uses `idle_reason`, the only per-row signal real telemetry
provides. `task_ground_truth.is_legitimate_idle_dominant` was computed by
the generator from a *different*, finer-grained internal signal (planned vs.
"extra" idle minutes) that isn't exposed in telemetry either — a real
deployment wouldn't have it available any more than `classify_idle()` does.
The gap is a genuinely harder, more realistic evaluation, not a coding
defect — and it never compromises the actually-required guarantee: the
truck-wait no-blame rate above, which is exactly 0%.

## Final intelligence layer

```
src/training/
  catalog.py            TRAINING_CATALOG (6 clips) + get_clip_for_trigger()
  recommend.py            recommend_training(), get_training_recommendation()
  effectiveness.py         evaluate_training_effect(), get_training_outcome()
  escalation.py             check_escalation()

src/safety/threat_briefing.py   generate_threat_briefing()

src/intelligence/
  explanations.py          explain_eta(), explain_operator_twin(), explain_habit(),
                             explain_idle(), explain_focus(), explain_risk(),
                             explain_diagnosis(), explain_training(), explain_threat_briefing()
  operator_state.py        generate_operator_state() — the unified entry point
  realtime.py                update_operator_state() — fast, no-retraining live updates

src/evaluation/intelligence_eval.py
  evaluate_training_recommendation_relevance(), evaluate_training_effectiveness(),
  evaluate_threat_briefing_correctness()
```

**Backend integration:** see [`ml/docs/integration.md`](docs/integration.md)
— the one document a backend developer needs, covering entry points, JSON
schemas, error handling, and model loading without reading every file.

### Just-in-Time Micro Training

`recommend_training()` is a pure rule function over already-computed
signals (Habit Radar, diagnosis, the Operator Twin, a proximity-event
count) — it never recomputes another module's logic itself.
`get_training_recommendation()` is the real-data convenience wrapper that
calls those modules and delegates to it. **Never recommends for a single
anomaly**: each trigger reuses an existing repetition guarantee (Habit
Radar's `is_habit`, diagnosis's multi-entity evidence requirement) or a new
evidence floor in `config.py` (`TRAINING_MIN_PROXIMITY_EVENTS`,
`TRAINING_MIN_TASKS_FOR_SENSITIVITY`). Only the single highest-priority
qualifying trigger is returned (safety triggers outrank efficiency ones),
mapped to one clip from the 6-item catalog. No LLM.

### Training effectiveness + instructor escalation

`evaluate_training_effect()` compares a "lower is better" behaviour metric
over the `TRAINING_OBSERVATION_WINDOW` (5) tasks/events before vs. after a
training event. **With fewer than 5 post-training observations, it returns
`status: "insufficient_evidence"` and `improvement: null` — never a
fabricated number.** Against the real generated dataset, the full range of
outcomes actually occurs across the seatbelt-habit operator's 6 training
checkpoints: `improving`, `no_change`, `worsening`, and
`insufficient_evidence` (both "too early" and "no more data left") all show
up — see the table in "Evaluating against ground truth" below.
`check_escalation()` only escalates on a **full** window showing
`"worsening"` or `"no_change"` — never on `insufficient_evidence`, and never
from a single bad observation.

### Pre-Task Threat Briefing

`generate_threat_briefing()` ranks fact-grounded candidate risks (a
detected habit, recent safety alerts, repeated site near-misses, a machine
degradation trend from the existing feature pipeline, weather scaled by the
operator's own Twin sensitivities, a historical afternoon effect) by
severity and returns the top 3. **An empty list is the honest "no
meaningful risk" answer** — never a fabricated placeholder risk.

### Structured explanations

Every `explain_*()` function in `src/intelligence/explanations.py` is a
thin adapter over a module's own already-computed reason/factor fields —
none of them recompute anything or invent a percentage. No LLM is used; if
an LLM-based narration layer is added later, these structured results are
what it should be built on top of, and remain the deterministic fallback.

### Unified operator intelligence

`generate_operator_state(operator_id, machine_id, task_id, current_context=None)`
orchestrates every module above into one result (see the schema in
`docs/integration.md` §4) — it contains no model/rule logic of its own.
`update_operator_state(previous_state, new_telemetry, ...)` is the
realtime path: dynamic ETA, remaining work, risk, and Focus are always
recomputed from the new row (cheap); the habit summary only rescans the
fleet when the new row actually completes a truck-wait transition (rare);
**the ETA model, the Operator Twin, and every loaded table are reused from
the cached `_context`** — nothing is retrained or reloaded from disk.

### Evaluating against ground truth (extended)

`run_intelligence_pipeline.py`'s evaluation section adds, on top of the
existing behaviour evaluation:

| Check | Result |
|---|---|
| Seatbelt-habit operator (`OP1005`) gets a training recommendation | `recommended=True`, `trigger_type=seatbelt_habit` |
| Inefficient operator (`OP1010`) has a real fuel finding | confirmed present (diagnosis correctly flags them) |
| A "quiet" operator (lowest habit frequency in the fleet) isn't over-flagged | confirmed not flagged for `seatbelt_habit` |
| Threat briefing weather/operator/machine-driven cases | all 3 structured checks pass |
| `OP1005`'s 6 real training checkpoints | full range observed: `improving`, `no_change`, `worsening`, `insufficient_evidence` (see below) |

Per-checkpoint detail for `OP1005` (seatbelt metric, chronological):

| Checkpoint | Before | After | Status |
|---|---|---|---|
| 1 | n/a (first-ever opportunity) | 0.20 | `no_baseline` |
| 2 | 0.20 | 0.00 | **improving** |
| 3 | 0.00 | 0.00 | `no_change` → escalate |
| 4 | 0.00 | 0.40 | `worsening` → escalate |
| 5 | 0.40 | 0.60 | `worsening` → escalate |
| 6 (most recent) | 0.60 | n/a (no tasks left in the window) | `insufficient_evidence` |

This is only what the synthetic data supports — **not a claim of
human-level or real-world training effectiveness**.

## How to run everything

**Requires Python 3.10+** (the codebase uses `X | None` union-type syntax). Verified with a clean install against a fresh virtualenv (Python 3.12) — see the production-readiness audit for details.

```bash
cd ml
python -m venv .venv
# Windows: .venv\Scripts\activate   |   macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt

# Generate synthetic data (only if missing) + build the feature dataset + save it:
python run_pipeline.py

# Force-regenerate the synthetic dataset from scratch first:
python run_pipeline.py --regenerate

# Train the ETA model (writes ml/models/eta/model.joblib + metadata.json)
# and run the full OP1001 / EXC001 / T001 demo:
python run_eta_pipeline.py --train

# Once a model is saved, just run the demo without retraining:
python run_eta_pipeline.py --demo-only

# Run Habit Radar / Idle Shield / Focus Battery / risk / diagnosis:
# ground-truth evaluation report + the OP1001/EXC001/T001 demo:
python run_behaviour_pipeline.py

# Run the unified intelligence layer (training, threat briefing, the full
# generate_operator_state() report) + a realtime-update demonstration:
python run_intelligence_pipeline.py

# Run the test suite:
python -m pytest tests/ -v
```

`run_pipeline.py` prints a summary (row counts per table, feature matrix
shape, split sizes, and a demo-scenario check) and exits non-zero on any
error — safe to wire into `/demo-check`. `run_eta_pipeline.py`,
`run_behaviour_pipeline.py`, and `run_intelligence_pipeline.py` do the same
for their respective subsystems.

### Inference interface (for the backend)

```python
from src.eta.model_io import load_eta_model
from src.eta.inference import predict_eta, predict_personalized_eta
from src.eta.dynamic import predict_dynamic_eta
from src.eta.remaining_work import calculate_remaining_work
from src.operator_twin.twin import build_operator_twin, get_operator_profile
```

All of these take **already feature-engineered** rows (one row of
`src.features.build_features.build_task_level_dataset()`'s output) or plain
dicts for the twin/explanation helpers — none of them re-run the feature
pipeline themselves, so the caller controls exactly which data feeds in.

**Input schema** — one row from the task-level feature DataFrame (55 columns:
task/operator/machine/weather static features + the `*_prior` historical
aggregates; see "Feature pipeline" above). **Output schema** —
`predict_personalized_eta()`:

```json
{
  "eta_min": 14.3,
  "eta_max": 33.4,
  "eta_point": 22.9,
  "original_eta": 32.5,
  "reason": "This operator typically runs faster than average.",
  "factors": [{"name": "weather", "impact": "positive", "detail": "clear conditions"}],
  "buckets_remaining": 65,
  "model_name": "linear_regression"
}
```

`predict_dynamic_eta()` returns the same shape plus `pct_complete` and
`cycle_time_change_pct`. `get_operator_profile()` returns the camelCase twin
shape shown in "Operator Twin" above.

### Example: OP1001 / EXC001 / T001

Running `python run_eta_pipeline.py --demo-only` after training prints, for
the deterministic demo scenario:

```
1) Baseline ETA (linear_regression): 22.9 min
   Naive planner estimate: 32.5 min | Actual recorded outcome: 30.6 min
2) Operator Twin for OP1001 (n_tasks=165): paceFactor=1.127, afternoonEffect=-0.126, ...
3) Personalized ETA range: eta_min=14.3, eta_max=33.4, point=22.9
4) Dynamic ETA (task halfway through): eta_min=23.6, eta_max=32.1, point=27.4
   "recent cycle time is running +21% vs. plan"
5) Main drivers: weather (positive), operator_pace (positive), machine_age (neutral)
```

(Exact numbers depend on the seed and current dataset — this is illustrative,
not a hardcoded claim; run it yourself to see the live values.)

### Behaviour + Safety inference interface (for the backend)

```python
from src.anomaly.habit_radar import detect_habits, get_habit_summary
from src.anomaly.idle_shield import classify_idle, classify_task_idle
from src.anomaly.diagnosis import diagnose_fuel_source
from src.safety.focus_battery import calculate_focus, get_focus_recommendation
from src.safety.risk import calculate_risk, get_risk_factors
```

`get_habit_summary()` and `classify_idle()`/`classify_task_idle()` take
telemetry rows/DataFrames directly (no feature pipeline needed).
`calculate_focus()` takes an `as_of` timestamp, `tasks_df`, `weather_df`, and
an Operator Twin profile (from `get_operator_profile()`). `calculate_risk()`
takes plain scalar context (seatbelt status, machine-moving flag, nearest
worker distance, recent alert count, weather, habit/degradation flags) — no
DataFrame required, so the backend can call it straight from a live
telemetry event.

**Output schema** — `calculate_risk()`:

```json
{
  "risk_level": "critical",
  "score": 100,
  "factors": ["seatbelt_unfastened_while_moving"],
  "explanation": "Machine is moving with the seatbelt unfastened — critical, non-negotiable.",
  "hard_rule_triggered": "seatbelt_unfastened_while_moving"
}
```

`get_habit_summary()`:

```json
{
  "operator_id": "OP1005",
  "habit_type": "seatbelt_during_truck_wait",
  "count": 7,
  "opportunities": 33,
  "frequency": 0.212,
  "z_score": 3.09,
  "is_habit": true,
  "explanation": "Seatbelt was repeatedly removed during truck waits and remained unfastened when movement resumed, at a rate well above the rest of the fleet (7 of 33 truck-wait opportunities, 21%, z=3.1 vs. fleet average 8%)."
}
```

### Example: OP1001 / EXC001 / T001 (Behaviour + Safety)

Running `python run_behaviour_pipeline.py` prints, for the demo scenario
(illustrative — run it yourself for live values):

```
1) Habit Radar for OP1001: is_habit=False (3/58 opportunities, 5.2%, z=-0.6
   — normal, not flagged)
2) Idle Shield for task T001: dominant_idle_type=avoidable (5.0 min, non-truck task)
3) Focus Battery for OP1001 at shift start: score=100, factors=[] (fresh shift, no penalties)
4) Risk intelligence for task T001: risk_level=low, score=10, no hard rule triggered
5) Diagnosis: OP1010 flagged (operator, +31% fuel across 8 machines),
   EXC002 flagged (machine, +29% fuel across 20 operators)
```

### Example: OP1001 / EXC001 / T001 (Unified Intelligence)

Running `python run_intelligence_pipeline.py` prints the full report
(operator twin, current/dynamic ETA, remaining work, risk, habits, idle
analysis, focus, training, threat brief, explanations) plus a realtime
progression. Illustrative excerpt:

```
TRAINING
  recommended: True
  clip_id: TR_SWING_ZONE
  reason: 10 recorded proximity/near-miss events for this operator.

PRE-TASK THREAT BRIEF
  [{'priority': 1, 'risk': "Workers have repeatedly entered this
    machine's swing zone recently.", 'source': 'site'}]

REALTIME UPDATE — telemetry rows applied one at a time (no model retraining)
  step 1: dynamic_eta.eta_point=26.5  buckets_remaining=53  risk_level=low
  step 2: dynamic_eta.eta_point=27.4  buckets_remaining=41  risk_level=low
  step 3: dynamic_eta.eta_point=27.4  buckets_remaining=29  risk_level=low
  step 4: dynamic_eta.eta_point=27.2  buckets_remaining=17  risk_level=low
```

See [`docs/integration.md`](docs/integration.md) for the full JSON
schema and how the backend should call this.

## Tests

`ml/tests/` (136 tests, all passing — see the production-readiness audit
below for full verification detail) covers:

- **`test_synthetic.py`** — generation is deterministic (same seed -> byte-identical
  output), every table is non-empty, demo IDs exist and resolve correctly,
  no impossible values, every planted pattern is actually present, and the
  degrading machine's cycle time measurably trends up over the window.
- **`test_loaders.py`** — every loader round-trips its table, ID columns stay
  strings (no leading-zero loss), unknown table names raise clearly.
- **`test_features.py`** — the feature matrix has no NaNs, `actual_time_min`
  is never in the usable feature-column list, each operator's *first* task
  has no history yet (proves no future row leaked backward), the degrading
  machine's trend feature is positive by the end of the window, and ETA /
  Operator Twin share the same underlying feature columns.
- **`test_splits.py`** — the time-aware split is strictly chronological with
  no overlap, roughly respects the requested fractions, and rejects invalid
  fraction combinations.
- **`test_eta_model.py`** — training compares ≥2 candidates using the same
  time-aware split, selection is by lowest validation MAE, MAE/RMSE/median-AE
  are all reported, and `predict_personalized_eta()` always returns a real
  interval (never a disguised single point).
- **`test_operator_twin.py`** — twin shape/coverage, the shrinkage formula
  itself (deterministic whitebox check), the fleet-average fallback for an
  operator with zero history, that the planted inefficient operator scores
  below fleet-average fuel efficiency, that rain-sensitivity direction
  correlates with the generator's own (legitimate, non-hidden) operator
  field, and that `as_of` strictly excludes tasks at/after the cutoff.
- **`test_dynamic_eta.py`** — remaining-work math (including that
  `trucks_remaining` is never fabricated), a constructed slow-cycle-time
  scenario is correctly detected and explained, interval width shrinks as a
  task nears completion, and the explanation module's factor directions are
  correct for rain / an old machine / a fast operator.
- **`test_habit_radar.py`** — a constructed repeated pattern is detected, a
  single event is never flagged, frequency math is exact, and the real
  dataset flags exactly the planted operator (`OP1005`), no one else.
- **`test_idle_shield.py`** — every legitimate idle reason classifies
  correctly, the hard no-blame rule holds for every variant of extra context
  on the row, a 500-row sample of real truck-wait telemetry never gets
  blamed, and the ground-truth evaluation reports a 0% false-blame rate.
- **`test_focus_battery.py`** — normal/prolonged-work/heat/afternoon
  scenarios move the score in the right direction, the score is bounded
  0-100 even under deliberately extreme inputs, and the disclaimer is always
  present and non-medical.
- **`test_risk.py`** — safe/medium scenarios score as expected, both hard
  rules (seatbelt, proximity) independently and jointly force `critical`
  with `score=100` regardless of how "fine" every contextual factor looks,
  and the hard rule reproduces the dataset's own `safety_alert` column with
  ~perfect precision/recall.
- **`test_diagnosis.py`** — the planted degrading machine (`EXC002`) and
  inefficient operator (`OP1010`) are both correctly flagged with zero false
  positives, and raising the minimum-entity bar shrinks results without
  erroring.
- **`test_training.py`** — recommendation triggers correctly per pattern
  type (habit, proximity, fuel, wet-weather, heat), never triggers on weak
  evidence, correctly prioritizes safety over efficiency, and effectiveness
  tracking/escalation covers incomplete windows, improving, no-change, and
  worsening cases (plus a real-data sanity check across `OP1005`'s actual
  checkpoints).
- **`test_threat_briefing.py`** — each risk source (weather, operator,
  machine, site) is correctly triggered, multiple risks rank by severity,
  the top-3 limit is enforced, priorities are sequential, and the no-risk
  case returns an honest empty list.
- **`test_operator_state.py`** — the complete output structure, that its
  numbers match calling the underlying modules directly (no orchestration
  drift), a clear error for an unknown task, a genuinely pre-task state
  (full remaining work) by default, and safe handling of missing optional
  context.
- **`test_realtime.py`** — ETA/risk/focus/habit updates from new telemetry,
  that the habit summary only rescans the fleet on a real transition (not
  every tick), that the cached ETA model object is reused (proof nothing
  retrains), and that remaining work strictly decreases across sequential
  updates.

## Production-readiness audit

A full end-to-end audit (data leakage, time-aware evaluation, ETA/interval
correctness, Habit Radar generalization, JSON serialization, error handling,
fresh-process artifact loading, clean-environment install, reproducibility,
and realtime performance) was performed against the actual code and output
— not just re-running the existing test suite. **6 real issues were found
and fixed**, each with a regression test:

| # | Issue | Fix |
|---|---|---|
| 1 | An out-of-distribution task row could make the raw ETA model prediction negative, and `eta_min`/`eta_max` were clamped independently of `eta_point` — producing a point estimate **outside its own reported range**. | `predict_eta()` floors the raw prediction at 1 minute; `predict_personalized_eta()`/`predict_dynamic_eta()` now also clamp the point estimate into `[eta_min, eta_max]` as a second line of defense. |
| 2 | `classify_idle()` had no guard against being called on a row that isn't actually idle (`machine_moving=True`) — it fell through to the "unrecognized reason" branch and confidently returned `"avoidable"`, a misleading result. | Added an explicit `idle_type: "not_idle"` result for non-idle rows. |
| 3 | `generate_operator_state()` never validated `operator_id`/`machine_id` against the data, and a `machine_id` that didn't match the task's real machine was silently accepted — producing an internally inconsistent state. | Added validation: unknown IDs and operator/machine mismatches now raise `ValueError` with a clear message. |
| 4 | `generate_operator_state()`'s "2nd call" was just as slow as the first (~4.4s) — a Habit Radar internal helper used a per-task Python loop over the full telemetry table (~2s of the total, on every call). | Vectorized the helper (`groupby(...).shift(1)` instead of a per-task loop) — same output, ~30ms instead of ~2s. Also added an optional `features_df` cache parameter so repeat calls can skip the feature-pipeline rebuild too. |
| 5 | `src.eta.model_io` (the pure inference/loading path) imported path constants from `src.eta.train`, coupling every inference-only caller to the training module's `sklearn` fitting imports. | Both modules now source `MODEL_PATH`/`METADATA_PATH` from `config.py` independently. |
| 6 | No documented Python version requirement, despite the codebase using `X \| None` union-type syntax (Python 3.10+). | Documented in `requirements.txt` and this README. |

**Verified (not just asserted):**
- **Clean-environment install + full pipeline**: a fresh virtualenv with only `requirements.txt` installed, data/model artifacts deleted and regenerated from scratch, produced byte-identical results and all 136 tests passing.
- **Fresh-process model loading**: `load_eta_model()` + `generate_operator_state()` work correctly in a process that never ran training.
- **JSON serialization**: the full public output of both `generate_operator_state()` and `update_operator_state()` (including a real telemetry row's numpy/NaN-bearing fields as input) serializes with plain `json.dumps()` — no custom encoder needed.
- **No data leakage**: re-confirmed via `test_features.py`'s no-lookahead checks and a fresh read of every `*_prior` feature's construction.
- **Hard safety rules**: confirmed unconditional — a habit/alert/weather context can elevate a *non-critical* score but can never downgrade the seatbelt/proximity hard rules (score stays 100, `risk_level` stays `critical`).
- **Habit Radar generalizes beyond `OP1005`**: a new regression test swaps the anomalous identity to an arbitrary operator and confirms detection follows the actual pattern, not a hardcoded ID.
- **Performance**: see the table in `docs/integration.md` §7 — realtime updates ~15ms, a cached `generate_operator_state()` call ~270ms.

**Known, real limitations (not hidden):**
- Idle Shield's task-level accuracy against the synthetic `task_ground_truth` label is ~47% — an honest, explained gap (two different internal signals in the generator), not a defect; the actually-required guarantee (0% false blame on truck-wait idle) holds exactly.
- `generate_operator_state()`'s cold-call cost (~1.7s, dominated by the one-time `sklearn` import) is real; callers making repeated calls should reuse `tables`/`features_df` as documented in `docs/integration.md`.
- The residual-quantile ETA interval is only as good as the validation set it's computed from (423 rows currently) — reasonable for this synthetic dataset, but not a claim of calibrated real-world uncertainty.

## Next step (not done here)

Nothing from this specification remains — the ML layer is complete and
integration-ready. Future work (not requested here) would be actual
frontend/backend wiring, and any LLM-based narration layered on top of the
structured explanations in `src/intelligence/explanations.py`.
