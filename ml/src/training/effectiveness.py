"""Training effectiveness: compares an operator's behaviour before vs. after
a training event, over the next `config.TRAINING_OBSERVATION_WINDOW` (5)
relevant tasks/events — never fewer, never fabricated.

Every metric here follows a "lower is better" (badness) convention so
`improvement = before - after` is positive when behaviour actually got
better, matching the spec's example (`before=0.40, after=0.10,
improvement=0.30`).
"""

import pandas as pd

from src.anomaly.habit_radar import _task_opportunities
from src.anomaly.idle_shield import classify_task_idle
from src.common import config
from src.common.time_utils import merge_asof_weather

# ---------------------------------------------------------------------------
# Per-topic metric series builders: operator_id -> DataFrame[task_id, start_time, value]
# ---------------------------------------------------------------------------


def _seatbelt_series(operator_id, tasks_df, telemetry_df, **_) -> pd.DataFrame:
    opp = _task_opportunities(telemetry_df)
    opp = opp[opp["operator_id"] == operator_id].copy()
    opp["value"] = (opp["unbuckled_during_idle"] & opp["unbuckled_at_resume"]).astype(float)
    return opp.merge(tasks_df[["task_id", "start_time"]], on="task_id", how="left")[
        ["task_id", "start_time", "value"]
    ]


def _idle_efficiency_series(operator_id, tasks_df, telemetry_df, **_) -> pd.DataFrame:
    op_tasks = tasks_df[tasks_df["operator_id"] == operator_id]
    idle_task_ids = telemetry_df[telemetry_df["idling_time_min"] > 0]["task_id"].unique()
    rows = []
    for _, task in op_tasks[op_tasks["task_id"].isin(idle_task_ids)].iterrows():
        result = classify_task_idle(task["task_id"], telemetry_df)
        rows.append(
            {
                "task_id": task["task_id"],
                "start_time": task["start_time"],
                "value": 1.0 if result["dominant_idle_type"] == "avoidable" else 0.0,
            }
        )
    return pd.DataFrame(rows, columns=["task_id", "start_time", "value"])


def _fuel_inefficiency_series(operator_id, tasks_df, telemetry_df, **_) -> pd.DataFrame:
    op_tasks = tasks_df[tasks_df["operator_id"] == operator_id]
    agg = (
        telemetry_df.groupby("task_id")
        .agg(fuel_used_l=("fuel_used_l", "sum"), moving_minutes=("machine_moving", "sum"))
        .reset_index()
    )
    agg["moving_minutes"] = agg["moving_minutes"].replace(0, pd.NA)
    agg["value"] = agg["fuel_used_l"] / agg["moving_minutes"]
    merged = op_tasks[["task_id", "start_time"]].merge(agg[["task_id", "value"]], on="task_id", how="inner")
    return merged.dropna(subset=["value"])


def _wet_weather_series(operator_id, tasks_df, weather_df=None, **_) -> pd.DataFrame:
    op_tasks = tasks_df[(tasks_df["operator_id"] == operator_id) & (tasks_df["weather"].isin(["rain", "storm"]))]
    out = op_tasks[["task_id", "start_time"]].copy()
    out["value"] = op_tasks["actual_time_min"] / op_tasks["estimated_time_min"].replace(0, pd.NA)
    return out.dropna(subset=["value"])


def _heat_performance_series(operator_id, tasks_df, weather_df=None, **_) -> pd.DataFrame:
    op_tasks = tasks_df[tasks_df["operator_id"] == operator_id].copy()
    merged = merge_asof_weather(op_tasks, weather_df, time_col="start_time") if weather_df is not None else op_tasks
    if "temperature" not in merged.columns:
        return pd.DataFrame(columns=["task_id", "start_time", "value"])
    hot = merged[merged["temperature"] > config.HEAT_TEMP_THRESHOLD_C]
    out = hot[["task_id", "start_time"]].copy()
    out["value"] = hot["actual_time_min"] / hot["estimated_time_min"].replace(0, pd.NA)
    return out.dropna(subset=["value"])


def _proximity_series(operator_id, tasks_df, near_misses_df=None, **_) -> pd.DataFrame:
    op_tasks = tasks_df[tasks_df["operator_id"] == operator_id]
    if near_misses_df is None:
        return pd.DataFrame(columns=["task_id", "start_time", "value"])
    near_miss_task_ids = set(near_misses_df["task_id"])
    out = op_tasks[["task_id", "start_time"]].copy()
    out["value"] = out["task_id"].isin(near_miss_task_ids).astype(float)
    return out


_METRIC_BUILDERS = {
    "seatbelt": _seatbelt_series,
    "idle_efficiency": _idle_efficiency_series,
    "fuel_inefficiency": _fuel_inefficiency_series,
    "wet_weather_performance": _wet_weather_series,
    "heat_performance": _heat_performance_series,
    "proximity": _proximity_series,
}


def evaluate_training_effect(
    operator_id: str,
    metric_type: str,
    training_time: pd.Timestamp,
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    near_misses_df: pd.DataFrame | None = None,
    weather_df: pd.DataFrame | None = None,
    window: int = config.TRAINING_OBSERVATION_WINDOW,
) -> dict:
    """Compare `window` observations before vs. after `training_time` for
    one operator on one behaviour metric. Never fabricates a result when
    there isn't enough post-training evidence yet.
    """
    if metric_type not in _METRIC_BUILDERS:
        raise ValueError(f"Unknown metric_type '{metric_type}'. Known: {sorted(_METRIC_BUILDERS)}")

    series = _METRIC_BUILDERS[metric_type](
        operator_id, tasks_df=tasks_df, telemetry_df=telemetry_df, near_misses_df=near_misses_df, weather_df=weather_df
    )
    series = series.sort_values("start_time")

    before = series[series["start_time"] < training_time].tail(window)
    after = series[series["start_time"] >= training_time].head(window)

    n_observations = len(after)

    if n_observations < window:
        return {
            "metric_type": metric_type,
            "before": round(float(before["value"].mean()), 3) if len(before) else None,
            "after": round(float(after["value"].mean()), 3) if len(after) else None,
            "improvement": None,
            "observations": n_observations,
            "status": "insufficient_evidence",
            "note": (
                f"Only {n_observations} of {window} required post-training observations available yet — "
                "not enough evidence to report a definitive result."
            ),
        }

    before_mean = float(before["value"].mean()) if len(before) else None
    after_mean = float(after["value"].mean())
    improvement = round(before_mean - after_mean, 3) if before_mean is not None else None

    if improvement is None:
        status = "no_baseline"
    elif improvement >= config.TRAINING_MEANINGFUL_IMPROVEMENT:
        status = "improving"
    elif improvement <= config.TRAINING_WORSENING_THRESHOLD:
        status = "worsening"
    else:
        status = "no_change"

    return {
        "metric_type": metric_type,
        "before": round(before_mean, 3) if before_mean is not None else None,
        "after": round(after_mean, 3),
        "improvement": improvement,
        "observations": n_observations,
        "status": status,
    }


def get_training_outcome(
    operator_id: str,
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    training_events_df: pd.DataFrame,
    near_misses_df: pd.DataFrame | None = None,
    weather_df: pd.DataFrame | None = None,
    module_to_metric: dict | None = None,
) -> dict:
    """Real-data convenience wrapper: finds the operator's most recent
    COMPLETED training event and evaluates its effect. Returns a clear
    "no training on record" result rather than erroring when there is none.
    """
    module_to_metric = module_to_metric or {"seatbelt_awareness": "seatbelt"}

    op_events = training_events_df[
        (training_events_df["operator_id"] == operator_id) & (training_events_df["completed"] == True)  # noqa: E712
    ].sort_values("timestamp")

    if len(op_events) == 0:
        return {"has_training_record": False, "note": "No completed training event on record for this operator."}

    latest = op_events.iloc[-1]
    metric_type = module_to_metric.get(latest["module"])
    if metric_type is None:
        return {
            "has_training_record": True,
            "module": latest["module"],
            "note": f"No effectiveness metric mapped for training module '{latest['module']}'.",
        }

    result = evaluate_training_effect(
        operator_id,
        metric_type,
        latest["timestamp"],
        tasks_df,
        telemetry_df,
        near_misses_df=near_misses_df,
        weather_df=weather_df,
    )
    return {"has_training_record": True, "module": latest["module"], "training_time": latest["timestamp"], **result}
