"""Idle Shield: classifies each idle telemetry interval as legitimate or
avoidable — and NEVER blames the operator for a truck-delay wait.

`idle_reason` is a real telemetry column (see `CLAUDE.md` §6), the same kind
of legitimately-available input the rest of the pipeline already uses (like
`fatigue_start_hour` on operators). Reading it isn't cheating; the "no-blame
guarantee" is enforced as a hard, unconditional rule rather than a learned
weight, exactly like the hard safety rules in `src.safety.risk` — a
`waiting_for_truck` reason can never come out "avoidable", full stop.
"""

import pandas as pd

from src.common import config


def classify_idle(idle_row: pd.Series | dict) -> dict:
    """Classify one idle telemetry row (or an equivalent dict).

    Hard rule, never overridden: `idle_reason == "waiting_for_truck"` (or any
    other configured legitimate reason) is always `"legitimate"`.

    Callers are expected to pass an actually-idle row (this is what
    `classify_task_idle()` below always does, pre-filtering on
    `idling_time_min > 0`). If a row that's plainly NOT idle is passed in
    directly (`machine_moving` true, or `idling_time_min` present and 0),
    this returns `idle_type: "not_idle"` rather than confidently guessing
    "avoidable" — a moving machine has no idle time to classify at all, and
    mislabeling it would be a misleading explanation, not a defensible one.
    """
    if idle_row.get("machine_moving") or (idle_row.get("idling_time_min", 1) == 0):
        return {
            "idle_type": "not_idle",
            "reason": "This telemetry row has no idle time to classify (machine is/was moving).",
            "confidence": 1.0,
        }

    reason = idle_row.get("idle_reason")

    if reason in config.LEGITIMATE_IDLE_REASONS:
        confidence = 0.95 if reason == "waiting_for_truck" else 0.85
        return {
            "idle_type": "legitimate",
            "reason": f"Idle attributed to {reason.replace('_', ' ')}.",
            "confidence": confidence,
        }

    if reason in config.AVOIDABLE_IDLE_REASONS:
        return {
            "idle_type": "avoidable",
            "reason": f"Idle attributed to {reason.replace('_', ' ')} — no operational cause recorded.",
            "confidence": 0.90,
        }

    # Unrecognized/missing reason on an idle row: be conservative rather than
    # silently assuming fault — flag as avoidable but with low confidence so
    # a human (or a higher-level system) knows this one needs a look.
    return {
        "idle_type": "avoidable",
        "reason": "Idle with no recognized reason recorded.",
        "confidence": 0.4,
    }


def classify_task_idle(task_id: str, telemetry_df: pd.DataFrame) -> dict:
    """Aggregate idle-minute breakdown for one task: how much of its idle
    time was legitimate vs. avoidable, and the dominant type."""
    task_telemetry = telemetry_df[telemetry_df["task_id"] == task_id]
    idle_rows = task_telemetry[task_telemetry["idling_time_min"] > 0]

    legitimate_min = 0.0
    avoidable_min = 0.0
    for _, row in idle_rows.iterrows():
        result = classify_idle(row)
        if result["idle_type"] == "legitimate":
            legitimate_min += row["idling_time_min"]
        elif result["idle_type"] == "avoidable":
            avoidable_min += row["idling_time_min"]
        # "not_idle" shouldn't occur here (idle_rows is already filtered to
        # idling_time_min > 0), but if it ever does, skip rather than
        # mis-attribute it to either bucket.

    total_min = legitimate_min + avoidable_min
    dominant = "legitimate" if legitimate_min >= avoidable_min else "avoidable"
    if total_min == 0:
        dominant = "legitimate"  # no idle at all -> nothing to blame

    return {
        "task_id": task_id,
        "legitimate_idle_min": round(legitimate_min, 1),
        "avoidable_idle_min": round(avoidable_min, 1),
        "total_idle_min": round(total_min, 1),
        "dominant_idle_type": dominant,
    }
