"""Orchestrates the full feature pipeline: raw tables -> one ML-ready,
task-level feature matrix.

This is the single function ETA, Operator Twin, and anomaly detection all
call (`CLAUDE.md` requirement: "reusable feature functions ... use the same
feature definitions"). Each of those packages' `dataset.py` just selects
which columns to use as `X` and which column to use as the target.
"""

import pandas as pd

from src.common.time_utils import merge_asof_weather
from src.features.machine_features import build_machine_features
from src.features.operator_features import build_operator_features
from src.features.task_features import build_task_features
from src.features.telemetry_features import (
    add_machine_history_features,
    add_operator_fuel_efficiency_features,
    add_operator_history_features,
)
from src.features.weather_features import build_weather_features

# Columns that must NEVER be used as model input (targets or only-known-after-the-fact).
LEAKAGE_COLUMNS = {"actual_time_min"}

ID_COLUMNS = ["task_id", "operator_id", "machine_id", "start_time"]


def build_task_level_dataset(
    tasks_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
) -> pd.DataFrame:
    """Build one row per task with static + time-aware historical features.

    Every `*_prior` column is computed using only tasks that started strictly
    before the current one (see `telemetry_features.py`) — safe to use as
    model input for predicting that task's outcome. `actual_time_min` is kept
    as the label column but is flagged in `LEAKAGE_COLUMNS` so callers don't
    accidentally feed it back in as a feature.
    """
    df = tasks_df.copy()

    df = add_operator_history_features(df)
    df = add_machine_history_features(df)
    df = add_operator_fuel_efficiency_features(df, telemetry_df)

    df = build_task_features(df)
    df = merge_asof_weather(df, build_weather_features(weather_df), time_col="start_time")

    operator_feats = build_operator_features(operators_df)
    df = df.merge(operator_feats, on="operator_id", how="left", suffixes=("", "_operator"))

    machine_feats = build_machine_features(machines_df)
    df = df.merge(machine_feats, on="machine_id", how="left", suffixes=("", "_machine"))

    df = df.sort_values("start_time").reset_index(drop=True)
    return df


def feature_columns(df: pd.DataFrame) -> list[str]:
    """Columns safe to use as model input: everything except IDs, raw
    categorical text (superseded by their dummy columns), and leakage columns."""
    raw_categorical = {"skill", "type", "task_type", "zone", "weather", "condition", "idle_reason"}
    exclude = set(ID_COLUMNS) | LEAKAGE_COLUMNS | raw_categorical | {"estimated_time_min"}
    return [c for c in df.columns if c not in exclude and df[c].dtype != object]
