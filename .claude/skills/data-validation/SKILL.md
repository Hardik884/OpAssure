---
name: data-validation
description: Validate the OpAssure synthetic dataset — record counts, missing values, timestamp consistency, entity relationships, planted anomalies, and ground-truth labels. Use after regenerating synthetic data, before an ML evaluation run, or when data looks suspicious.
---

# Data Validation

Validates `data/synthetic/` and `data/ground_truth/` against the data model and
planted-problem list in `CLAUDE.md` §6.

## Checks to run

1. **Expected scale**
   - 20 operators, 8 machines, 60 days of data (or whatever the current generator
     config specifies — check `backend/simulator/` for the actual config first
     rather than assuming the numbers in CLAUDE.md were never changed).

2. **Missing values**
   - No unexpected nulls in required fields (see field lists in `CLAUDE.md` §6 for
     each table).
   - Where a field is legitimately nullable (e.g. `idle_reason` when not idling),
     confirm the null pattern makes sense.

3. **Timestamp consistency**
   - Telemetry timestamps are monotonically sensible per machine/operator (no
     impossible time travel).
   - Task `start_time` + duration doesn't overlap impossibly with other tasks for
     the same operator or machine.
   - Weather timestamps cover the full 60-day window without large gaps.

4. **Entity relationships**
   - Every `operator_id` in `tasks`/`telemetry` exists in `operators`.
   - Every `machine_id` in `tasks`/`telemetry` exists in `machines`.
   - Every `task_id` referenced elsewhere exists in `tasks`.
   - Demo identifiers `OP1001`, `EXC001`, `T001` exist and are linked correctly.

5. **Impossible values**
   - No negative durations, fuel, volumes, or distances.
   - Percentages/probabilities (e.g. `belt_skip_probability_when_idle`) are in
     [0, 1].
   - Lat/lon values fall within the expected site bounds.
   - `seatbelt_status` and `machine_moving` use consistent, documented value sets.

6. **Planted anomalies present and labeled**
   For each of the six planted problems in `CLAUDE.md` §6, confirm:
   - the pattern is actually present in the data (not just described in a
     generator comment), and
   - a corresponding `ground_truth_labels` row exists.

   Specifically:
   - Seatbelt habit — traceable to a specific operator+pattern.
   - Afternoon slowdown — visible pace drop after ~2–3 PM, worse with heat.
   - Machine degradation — one machine's fuel/cycle metrics trend worse over time,
     affecting all operators who use it.
   - Operator inefficiency — one operator's fuel use is consistently higher across
     multiple machines.
   - Legitimate idle — present and distinguishable from problematic idle via
     `idle_reason`.
   - Proximity near-misses — worker_positions repeatedly entering machine
     swing-zones, with corresponding `near_misses` rows.

## Output

Report as a checklist (pass/fail per check above) with specifics — row counts,
example offending rows, or the query used — not just "looks fine" or "data is
bad". End with a one-line overall verdict: `DATA VALIDATION: PASS` or
`DATA VALIDATION: FAIL` with the failing checks listed. Do not modify the
generator or the data as part of this skill unless explicitly asked to fix an
issue.
