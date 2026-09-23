"""Just-in-Time Micro Training: recommendation, effectiveness tracking, and
instructor escalation.

- `catalog.py` — the internal training clip catalog.
- `recommend.py` — `recommend_training()` / `get_training_recommendation()`,
  mapping detected Habit Radar / diagnosis / Operator Twin signals to a clip.
- `effectiveness.py` — `evaluate_training_effect()` / `get_training_outcome()`,
  comparing behaviour before vs. after a training event.
- `escalation.py` — `check_escalation()`, deterministic instructor escalation
  when a full observation window shows no improvement.
"""
