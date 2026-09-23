"""Operator Twin: a per-operator profile summarizing observed pace, weather
sensitivity, afternoon effect, fuel efficiency, and a seatbelt-behavior
indicator — built from historical data, not from the generator's hidden
ground-truth parameters (those exist only to plant the patterns; the twin
has to *find* them from tasks/telemetry like a real system would).

Sign conventions (all on a "speed" scale, so the numbers read consistently):
  - pace_factor > 1.0      -> faster than the fleet average
  - rain_sensitivity > 0   -> gets slower in rain (magnitude = how much)
  - heat_sensitivity  > 0   -> gets slower in heat
  - afternoon_effect  < 0   -> gets slower in the afternoon (matches the
    planted "afternoon slowdown" pattern being an unfavorable effect)
  - fuel_efficiency  > 1.0  -> uses less fuel than the fleet average

Operators with little history get shrunk toward the fleet average
(`config.OPERATOR_TWIN_SHRINKAGE_K`) instead of producing a noisy, overfit
number from 1-2 tasks.
"""

import pandas as pd

from src.common import config


def _duration_ratio(df: pd.DataFrame) -> pd.Series:
    """actual/estimated — the raw "how much longer than planned" signal
    everything else in this module is built from."""
    return df["actual_time_min"] / df["estimated_time_min"].replace(0, pd.NA)


def _shrink(operator_value: float, fleet_value: float, n: int, k: int = config.OPERATOR_TWIN_SHRINKAGE_K) -> float:
    """Empirical-Bayes-style shrinkage: weight = n / (n + k)."""
    if n <= 0:
        return fleet_value
    weight = n / (n + k)
    return weight * operator_value + (1 - weight) * fleet_value


def _task_fuel_per_moving_min(telemetry_df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        telemetry_df.groupby("task_id")
        .agg(fuel_used_l=("fuel_used_l", "sum"), moving_minutes=("machine_moving", "sum"))
        .reset_index()
    )
    agg["moving_minutes"] = agg["moving_minutes"].replace(0, pd.NA)
    agg["fuel_per_moving_min"] = agg["fuel_used_l"] / agg["moving_minutes"]
    return agg[["task_id", "fuel_per_moving_min"]]


def _seatbelt_violation_rate(telemetry_df: pd.DataFrame) -> pd.DataFrame:
    moving = telemetry_df[telemetry_df["machine_moving"]]
    rate = moving.groupby("operator_id")["safety_alert"].mean()
    n = moving.groupby("operator_id")["safety_alert"].size()
    return pd.DataFrame({"seatbelt_violation_rate": rate, "n_moving_intervals": n})


def build_operator_twin(
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> pd.DataFrame:
    """Build the twin for every operator with at least one task.

    Pass `as_of` to compute the twin using only tasks that started strictly
    before that timestamp — used by dynamic ETA so a running task never
    informs its own operator's profile. Omit it (the default) for a
    full-history snapshot, e.g. for a dashboard or the demo script.
    """
    tasks = tasks_df.copy()
    if as_of is not None:
        tasks = tasks[tasks["start_time"] < as_of]

    if len(tasks) == 0:
        return pd.DataFrame(
            columns=[
                "operator_id",
                "n_tasks",
                "pace_factor",
                "rain_sensitivity",
                "heat_sensitivity",
                "afternoon_effect",
                "fuel_efficiency",
                "seatbelt_violation_rate",
            ]
        )

    tasks = tasks.merge(operators_df[["operator_id", "fatigue_start_hour"]], on="operator_id", how="left")
    tasks["ratio"] = _duration_ratio(tasks)
    tasks["hour_of_day"] = pd.to_datetime(tasks["start_time"]).dt.hour + pd.to_datetime(tasks["start_time"]).dt.minute / 60.0
    tasks["is_afternoon"] = tasks["hour_of_day"] >= tasks["fatigue_start_hour"].fillna(config.DEFAULT_AFTERNOON_HOUR)
    tasks["is_wet"] = tasks["weather"].isin(["rain", "storm"])

    fuel = _task_fuel_per_moving_min(telemetry_df[telemetry_df["task_id"].isin(tasks["task_id"])])
    tasks = tasks.merge(fuel, on="task_id", how="left")

    fleet_ratio = tasks["ratio"].mean()
    fleet_wet_ratio = tasks.loc[tasks["is_wet"], "ratio"].mean()
    fleet_dry_ratio = tasks.loc[~tasks["is_wet"], "ratio"].mean()
    fleet_fuel = tasks["fuel_per_moving_min"].mean()

    rows = []
    for operator_id, g in tasks.groupby("operator_id"):
        n = len(g)
        op_ratio = g["ratio"].mean()
        pace_factor = _shrink(fleet_ratio / op_ratio if op_ratio else 1.0, 1.0, n)

        wet = g[g["is_wet"]]
        dry = g[~g["is_wet"]]
        if len(wet) >= 2 and len(dry) >= 2:
            wet_ratio, dry_ratio = wet["ratio"].mean(), dry["ratio"].mean()
            raw_rain_sensitivity = max(0.0, (wet_ratio / dry_ratio) - 1.0)
        else:
            raw_rain_sensitivity = max(0.0, (fleet_wet_ratio / fleet_dry_ratio) - 1.0) if pd.notna(fleet_wet_ratio) and pd.notna(fleet_dry_ratio) else 0.0
        rain_sensitivity = _shrink(raw_rain_sensitivity, 0.10, min(len(wet), len(dry)))

        afternoon = g[g["is_afternoon"]]
        morning = g[~g["is_afternoon"]]
        if len(afternoon) >= 2 and len(morning) >= 2:
            aft_ratio, morn_ratio = afternoon["ratio"].mean(), morning["ratio"].mean()
            raw_afternoon_effect = -max(0.0, (aft_ratio - morn_ratio) / morn_ratio) if morn_ratio else 0.0
        else:
            raw_afternoon_effect = 0.0
        afternoon_effect = _shrink(raw_afternoon_effect, -0.05, min(len(afternoon), len(morning)))

        op_fuel = g["fuel_per_moving_min"].mean()
        n_fuel = g["fuel_per_moving_min"].notna().sum()
        fuel_efficiency = _shrink(
            (fleet_fuel / op_fuel) if op_fuel and pd.notna(op_fuel) else 1.0, 1.0, n_fuel
        )

        rows.append(
            {
                "operator_id": operator_id,
                "n_tasks": n,
                "pace_factor": round(float(pace_factor), 3),
                "rain_sensitivity": round(float(rain_sensitivity), 3),
                "afternoon_effect": round(float(afternoon_effect), 3),
                "fuel_efficiency": round(float(fuel_efficiency), 3),
            }
        )

    twin_df = pd.DataFrame(rows)

    # Heat sensitivity needs task-level temperature, which requires an as-of
    # weather merge — computed separately (not in the loop above) to avoid
    # re-merging weather once per operator.
    heat_df = _heat_sensitivity(tasks)
    twin_df = twin_df.merge(heat_df, on="operator_id", how="left")
    twin_df["heat_sensitivity"] = twin_df["heat_sensitivity"].fillna(0.0).round(3)

    safety = _seatbelt_violation_rate(telemetry_df[telemetry_df["task_id"].isin(tasks["task_id"])])
    fleet_violation_rate = safety["seatbelt_violation_rate"].mean() if len(safety) else 0.0
    safety = safety.reset_index().rename(columns={"index": "operator_id"})
    twin_df = twin_df.merge(safety, on="operator_id", how="left")
    twin_df["seatbelt_violation_rate"] = twin_df.apply(
        lambda r: round(
            _shrink(
                r["seatbelt_violation_rate"] if pd.notna(r["seatbelt_violation_rate"]) else fleet_violation_rate,
                fleet_violation_rate,
                r["n_moving_intervals"] if pd.notna(r["n_moving_intervals"]) else 0,
            ),
            4,
        ),
        axis=1,
    )
    twin_df = twin_df.drop(columns=["n_moving_intervals"])

    return twin_df.sort_values("operator_id").reset_index(drop=True)


def _heat_sensitivity(tasks_with_ratio: pd.DataFrame) -> pd.DataFrame:
    """Compare each operator's duration ratio on hot vs. non-hot tasks.

    Needs the weather table (for temperature, not just condition), so it's
    merged separately from the main loop above.
    """
    from src.common.loaders import load_weather
    from src.common.time_utils import merge_asof_weather

    weather_df = load_weather()
    merged = merge_asof_weather(tasks_with_ratio, weather_df, time_col="start_time")
    merged["is_hot"] = merged["temperature"] > config.HEAT_TEMP_THRESHOLD_C

    rows = []
    for operator_id, g in merged.groupby("operator_id"):
        hot = g[g["is_hot"]]
        cool = g[~g["is_hot"]]
        if len(hot) >= 2 and len(cool) >= 2:
            hot_ratio, cool_ratio = hot["ratio"].mean(), cool["ratio"].mean()
            raw = max(0.0, (hot_ratio / cool_ratio) - 1.0) if cool_ratio else 0.0
        else:
            raw = 0.0
        heat_sensitivity = _shrink(raw, 0.10, min(len(hot), len(cool)))
        rows.append({"operator_id": operator_id, "heat_sensitivity": heat_sensitivity})
    return pd.DataFrame(rows)


def get_operator_profile(
    operator_id: str,
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    as_of: pd.Timestamp | None = None,
) -> dict:
    """Return one operator's twin as the camelCase dict shape used at the
    API boundary (this is what the backend would receive)."""
    twin_df = build_operator_twin(tasks_df, telemetry_df, operators_df, as_of=as_of)
    row = twin_df[twin_df["operator_id"] == operator_id]
    if len(row) == 0:
        # No history at all (as_of before the operator's first task, or an
        # operator with zero tasks) -> fleet-neutral defaults, not a crash.
        return {
            "operatorId": operator_id,
            "paceFactor": 1.0,
            "rainSensitivity": 0.10,
            "heatSensitivity": 0.10,
            "afternoonEffect": -0.05,
            "fuelEfficiency": 1.0,
            "seatbeltViolationRate": 0.0,
            "nTasks": 0,
        }

    r = row.iloc[0]
    return {
        "operatorId": operator_id,
        "paceFactor": r["pace_factor"],
        "rainSensitivity": r["rain_sensitivity"],
        "heatSensitivity": r["heat_sensitivity"],
        "afternoonEffect": r["afternoon_effect"],
        "fuelEfficiency": r["fuel_efficiency"],
        "seatbeltViolationRate": r["seatbelt_violation_rate"],
        "nTasks": int(r["n_tasks"]),
    }
