# OpAssure — AI/ML

**Owner:** AI/ML developer
**Stack:** Python, pandas, numpy, scikit-learn

> **Status:** data foundation + the ETA / Operator Twin subsystem are built and
> tested. Habit Radar, Idle Shield, Focus Battery, safety risk intelligence, and
> training recommendations are **not** implemented yet — that's the next step.
> See `CLAUDE.md` §11 for ML principles and §8 for the priority system.

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

## How to run everything

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

# Run the test suite:
python -m pytest tests/ -v
```

`run_pipeline.py` prints a summary (row counts per table, feature matrix
shape, split sizes, and a demo-scenario check) and exits non-zero on any
error — safe to wire into `/demo-check`. `run_eta_pipeline.py` does the same
for training + inference.

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

## Tests

`ml/tests/` (48 tests) covers:

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

## Next step (not done here)

Habit Radar, Idle Shield, Focus Battery, safety risk intelligence, and
training recommendation models — intentionally out of scope for this step
per the task instructions.
