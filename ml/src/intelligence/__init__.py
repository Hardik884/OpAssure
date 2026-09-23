"""The orchestration layer: combines the already-built, already-tested
individual modules (ETA, Operator Twin, Habit Radar, Idle Shield, Focus
Battery, risk, diagnosis, training) into one unified operator state, without
duplicating any of their logic.

- `explanations.py` — structured, deterministic explanation adapters for
  every subsystem (repackages each module's own already-computed reason/
  factor fields into one consistent shape; never invents new numbers).
- `operator_state.py` — `generate_operator_state()`, the single high-level
  entry point.
- `realtime.py` — `update_operator_state()`, a fast, no-retraining update
  path for live telemetry during an active task.
"""
