"""Focus Battery: a personalized, deterministic 0-100 OPERATIONAL indicator.

This is a workload/scheduling signal built from measurable inputs (hours
worked, time of day, heat, recent cycle-time deterioration, the operator's
own historical afternoon pattern, task-count repetition) — explicitly NOT a
medical or clinical fatigue measurement. Every call is deterministic: same
inputs always produce the same score and factor list, no hidden randomness.
"""

import pandas as pd

from src.common import config

DISCLAIMER = "Operational workload indicator only — not a medical or clinical fatigue measurement."


def _continuous_work_hours(operator_tasks: pd.DataFrame, as_of: pd.Timestamp) -> float:
    """Hours worked back-to-back (no gap >= FOCUS_BREAK_GAP_MIN) ending at
    or before `as_of`, on the same calendar day."""
    day_tasks = operator_tasks[
        (pd.to_datetime(operator_tasks["start_time"]).dt.date == as_of.date())
        & (pd.to_datetime(operator_tasks["start_time"]) <= as_of)
    ].sort_values("start_time")

    if len(day_tasks) == 0:
        return 0.0

    total_min = 0.0
    prev_end = None
    for _, task in day_tasks.iterrows():
        start = pd.to_datetime(task["start_time"])
        full_duration_min = float(task["actual_time_min"])
        end = start + pd.Timedelta(minutes=full_duration_min)

        if prev_end is not None and (start - prev_end).total_seconds() / 60.0 > config.FOCUS_BREAK_GAP_MIN:
            total_min = 0.0  # a real break resets the continuous-work clock

        # If this task is still in progress at `as_of`, only count the
        # elapsed portion — not the full (not-yet-worked) duration.
        elapsed_min = min(full_duration_min, max(0.0, (as_of - start).total_seconds() / 60.0))
        total_min += elapsed_min
        prev_end = end

    return round(total_min / 60.0, 2)


def calculate_focus(
    operator_id: str,
    as_of: pd.Timestamp,
    tasks_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    operator_twin: dict,
    recent_cycle_time_ratio: float | None = None,
) -> dict:
    """Compute the focus score for one operator at a point in time.

    `recent_cycle_time_ratio` (recent avg_cycle_time_s / that operator's own
    baseline) is optional — pass it when telemetry for an in-progress task is
    available; omitted, that factor simply contributes nothing.
    """
    operator_tasks = tasks_df[tasks_df["operator_id"] == operator_id]

    score = 100.0
    factors = []

    # --- continuous work duration ---------------------------------------
    hours = _continuous_work_hours(operator_tasks, as_of)
    if hours >= 3:
        penalty = min(30.0, (hours - 2) * 6)
        score -= penalty
        factors.append(f"{hours:.1f} hours of continuous work")

    # --- heat -------------------------------------------------------------
    weather_sorted = weather_df.sort_values("timestamp")
    idx = weather_sorted["timestamp"].searchsorted(as_of, side="right") - 1
    idx = max(0, min(idx, len(weather_sorted) - 1))
    temperature = float(weather_sorted.iloc[idx]["temperature"]) if len(weather_sorted) else 20.0
    if temperature > config.HEAT_TEMP_THRESHOLD_C:
        heat_excess = temperature - config.HEAT_TEMP_THRESHOLD_C
        heat_sensitivity = operator_twin.get("heatSensitivity", 0.1)
        penalty = min(20.0, heat_excess * (1.0 + heat_sensitivity * 5))
        score -= penalty
        factors.append("high temperature" if heat_excess < 8 else "very high temperature")

    # --- afternoon pattern (personalized via the Operator Twin) -----------
    hour_of_day = as_of.hour + as_of.minute / 60.0
    afternoon_effect = operator_twin.get("afternoonEffect", 0.0)
    if hour_of_day >= config.DEFAULT_AFTERNOON_HOUR and afternoon_effect < -0.03:
        penalty = min(20.0, abs(afternoon_effect) * 100)
        score -= penalty
        factors.append("historical afternoon slowdown")

    # --- recent cycle-time deterioration -----------------------------------
    if recent_cycle_time_ratio is not None and recent_cycle_time_ratio > 1.10:
        penalty = min(15.0, (recent_cycle_time_ratio - 1.0) * 50)
        score -= penalty
        factors.append("recent cycle time is running slower than usual")

    # --- repetitive workload -----------------------------------------------
    tasks_today = len(
        operator_tasks[
            (pd.to_datetime(operator_tasks["start_time"]).dt.date == as_of.date())
            & (pd.to_datetime(operator_tasks["start_time"]) <= as_of)
        ]
    )
    if tasks_today > config.FOCUS_REPETITIVE_TASK_THRESHOLD:
        penalty = min(15.0, (tasks_today - config.FOCUS_REPETITIVE_TASK_THRESHOLD) * 3)
        score -= penalty
        factors.append(f"{tasks_today} repetitive tasks completed today")

    score = round(max(0.0, min(100.0, score)))

    return {
        "operator_id": operator_id,
        "score": score,
        "factors": factors,
        "disclaimer": DISCLAIMER,
    }


def get_focus_recommendation(focus_result: dict) -> dict:
    """Deterministic recommendation from a `calculate_focus()` result."""
    score = focus_result["score"]
    if score < 50:
        recommendation = "Consider a 10-minute break after the next truck."
    elif score < 70:
        recommendation = "Stay alert — consider a short break at the next natural pause."
    else:
        recommendation = "No action needed — focus indicator looks good."

    return {**focus_result, "recommendation": recommendation}
