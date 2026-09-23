# OpAssure — AI/ML

**Owner:** AI/ML developer
**Stack:** Python, pandas, numpy, scikit-learn

> **Status:** ML foundation only — data generation, loading, and feature engineering.
> No models are trained yet (that's the next step). See `CLAUDE.md` §11 for ML
> principles and §8 for the priority system this foundation supports.

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

# Run the test suite:
python -m pytest tests/ -v
```

`run_pipeline.py` prints a summary (row counts per table, feature matrix
shape, split sizes, and a demo-scenario check) and exits non-zero on any
error — safe to wire into `/demo-check`.

## Tests

`ml/tests/` covers:

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

## Next step (not done here)

Training actual models (gradient boosting for ETA, etc.) against this
feature matrix, evaluated with `/ml-evaluation` — intentionally out of scope
for this step per the task instructions ("do NOT move to advanced models
yet").
