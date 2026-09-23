"""Just-in-Time Micro Training: a deterministic recommendation engine that
maps ALREADY-DETECTED behaviour/risk (from Habit Radar, Idle Shield, Focus
Battery, risk intelligence, the Operator Twin, and fuel diagnosis) to a
short training clip.

`recommend_training()` is the pure rule function — it takes already-computed
signals as arguments so it never re-runs another module's logic itself and
is trivially testable with synthetic inputs. `get_training_recommendation()`
is the real-data convenience wrapper that calls the other modules and then
delegates to `recommend_training()`.

Nothing here needs an LLM — it's a fixed, ordered set of "is this pattern
repeated/meaningful enough" checks against the same evidence thresholds the
underlying modules already use (Habit Radar's `is_habit`, diagnosis's
distinct-entity requirement, etc.), plus a couple of new ones in
`config.py` for signals that don't already have their own module
(wet-weather / heat performance, proximity-event repetition).
"""

import pandas as pd

from src.common import config
from src.training.catalog import get_clip_for_trigger

# Priority order when multiple triggers qualify at once: safety first.
_TRIGGER_PRIORITY = [
    "seatbelt_habit",
    "proximity_event",
    "fuel_inefficiency",
    "wet_weather_performance",
    "heat_performance",
]

_SAFE_TIMING = {
    "seatbelt_habit": "truck_wait",
    "proximity_event": "post_task",
    "fuel_inefficiency": "post_task",
    "wet_weather_performance": "pre_task",
    "heat_performance": "pre_task",
}

_REASON_TEMPLATES = {
    "seatbelt_habit": "Repeated seatbelt-during-truck-wait pattern detected ({count}/{opportunities} occurrences).",
    "proximity_event": "{count} recorded proximity/near-miss events for this operator.",
    "fuel_inefficiency": "Fuel use is consistently elevated across {n} machines ({ratio:+.0%} vs. fleet average).",
    "wet_weather_performance": "Rain sensitivity is elevated ({sensitivity:.0%}) across {n} recorded tasks.",
    "heat_performance": "Heat sensitivity is elevated ({sensitivity:.0%}) across {n} recorded tasks.",
}


def recommend_training(
    habit_summary: dict | None = None,
    proximity_event_count: int = 0,
    fuel_finding: dict | None = None,
    operator_twin: dict | None = None,
) -> dict:
    """Decide whether a training recommendation is warranted, from
    already-computed signals. Only ever recommends ONE clip — the
    highest-priority qualifying trigger — never a flood of suggestions."""
    triggered: dict[str, dict] = {}

    if habit_summary and habit_summary.get("is_habit"):
        triggered["seatbelt_habit"] = {
            "reason": _REASON_TEMPLATES["seatbelt_habit"].format(
                count=habit_summary["count"], opportunities=habit_summary["opportunities"]
            )
        }

    if proximity_event_count >= config.TRAINING_MIN_PROXIMITY_EVENTS:
        triggered["proximity_event"] = {
            "reason": _REASON_TEMPLATES["proximity_event"].format(count=proximity_event_count)
        }

    if fuel_finding and fuel_finding.get("source") == "operator":
        triggered["fuel_inefficiency"] = {
            "reason": _REASON_TEMPLATES["fuel_inefficiency"].format(
                n=fuel_finding["n_distinct_entities"], ratio=fuel_finding["ratio_vs_fleet"] - 1
            )
        }

    if operator_twin and operator_twin.get("nTasks", 0) >= config.TRAINING_MIN_TASKS_FOR_SENSITIVITY:
        if operator_twin.get("rainSensitivity", 0) >= config.TRAINING_SENSITIVITY_THRESHOLD:
            triggered["wet_weather_performance"] = {
                "reason": _REASON_TEMPLATES["wet_weather_performance"].format(
                    sensitivity=operator_twin["rainSensitivity"], n=operator_twin["nTasks"]
                )
            }
        if operator_twin.get("heatSensitivity", 0) >= config.TRAINING_SENSITIVITY_THRESHOLD:
            triggered["heat_performance"] = {
                "reason": _REASON_TEMPLATES["heat_performance"].format(
                    sensitivity=operator_twin["heatSensitivity"], n=operator_twin["nTasks"]
                )
            }

    for trigger_type in _TRIGGER_PRIORITY:
        if trigger_type not in triggered:
            continue
        clip = get_clip_for_trigger(trigger_type)
        if clip is None:
            continue  # a real trigger with no catalog content yet — skip, don't fabricate a clip
        return {
            "recommended": True,
            "clip_id": clip["clip_id"],
            "title": clip["title"],
            "reason": triggered[trigger_type]["reason"],
            "duration_seconds": clip["duration_seconds"],
            "safe_timing": _SAFE_TIMING[trigger_type],
            "trigger_type": trigger_type,
        }

    return {"recommended": False, "reason": "No sufficiently repeated or meaningful pattern found."}


def get_training_recommendation(
    operator_id: str,
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    near_misses_df: pd.DataFrame,
    operator_twin: dict | None = None,
) -> dict:
    """Real-data convenience wrapper: runs the underlying modules for one
    operator, then delegates to `recommend_training()`."""
    from src.anomaly.diagnosis import diagnose_fuel_source
    from src.anomaly.habit_radar import get_habit_summary
    from src.operator_twin.twin import get_operator_profile

    habit_summary = get_habit_summary(operator_id, telemetry_df)

    operator_task_ids = set(tasks_df[tasks_df["operator_id"] == operator_id]["task_id"])
    proximity_event_count = int(near_misses_df[near_misses_df["task_id"].isin(operator_task_ids)].shape[0])

    fuel_findings = diagnose_fuel_source(tasks_df, telemetry_df)
    fuel_finding = next(
        (f for f in fuel_findings if f.get("source") == "operator" and f.get("operator_id") == operator_id), None
    )

    twin = operator_twin or get_operator_profile(operator_id, tasks_df, telemetry_df, operators_df)

    return recommend_training(
        habit_summary=habit_summary,
        proximity_event_count=proximity_event_count,
        fuel_finding=fuel_finding,
        operator_twin=twin,
    )
