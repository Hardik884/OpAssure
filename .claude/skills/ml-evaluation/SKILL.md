---
name: ml-evaluation
description: Run and evaluate OpAssure ML models (ETA, Habit Radar, Idle Shield, risk detection, machine/operator diagnosis) against the project's ground-truth data. Use when asked to check model accuracy, run an evaluation, compare model versions, or investigate whether a model is leaking data.
---

# ML Evaluation

Evaluates OpAssure's ML components against `data/ground_truth/`. See `CLAUDE.md`
§6 (planted synthetic problems + ground truth) and §11 (ML principles) for the
stable facts this evaluation relies on.

## Before running anything

- Confirm `data/ground_truth/` and the relevant synthetic dataset exist. If not,
  stop and say so — do not evaluate against missing/stale data.
- Confirm the model(s) being evaluated were **not** trained on the same rows used
  for evaluation. If train/eval split information isn't available, flag this as a
  risk rather than assuming it's fine.

## What to evaluate, per model

- **ETA** — compare predicted `estimated_time_min` vs actual `actual_time_min`.
  Report MAE, MAPE, and error broken down by task_type and weather condition
  (checks the "afternoon slowdown" and weather-sensitivity planted patterns are
  actually being captured, not averaged away).
- **Habit Radar / behavioural pattern detection** — precision/recall against the
  planted patterns in ground truth (seatbelt habit, operator inefficiency,
  machine degradation). Report false-positive rate specifically for the
  "legitimate idle" case — a model that flags legitimate truck-wait idling as a
  habit is a real failure, not a rounding error.
- **Idle Shield** — precision/recall distinguishing legitimate idle (waiting for
  trucks) from problematic idle.
- **Risk detection / proximity** — recall on planted proximity near-misses; false
  positive rate on normal worker movement.
- **Machine vs. operator diagnosis** — when both a machine-degradation pattern and
  an operator-inefficiency pattern are planted, check the model attributes each to
  the correct source rather than conflating them.

## Data leakage checks

- No row used to compute a feature should include information from after the
  prediction timestamp.
- No ground-truth label field should appear (directly or via a derived feature)
  in the model's input features.
- If cross-validation is used, splits should respect time order or entity
  grouping (e.g. don't split telemetry rows from the same task across train/test).

## Output

Report metrics per model, then a short pass/fail judgment per model against a
reasonable bar (state the bar you're using, e.g. "MAE under 15% of mean task
duration"). Call out any planted pattern that isn't being detected at all —
that's a priority fix, not a metrics footnote. Do not tune hyperparameters or
change model code as part of running this skill — report findings and let the ML
owner (Person 3, per `CLAUDE.md` §5) decide next steps, unless explicitly asked to
fix something.
