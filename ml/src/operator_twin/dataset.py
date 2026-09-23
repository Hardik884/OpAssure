"""Operator Twin dataset.

The Operator Twin is a personalized profile, not a separate feature set — it
reuses the exact same task-level feature pipeline as ETA/anomaly, but the
target is the *personalization gap*: how much this operator's actual
performance differs from the naive planner estimate. That gap is what the
Operator Twin should learn to predict per operator.
"""

import pandas as pd

from src.features.build_features import build_task_level_dataset, feature_columns

TARGET_COLUMN = "estimate_error_min"


def build_operator_twin_dataset(
    tasks_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Return (full_feature_df, target_series, feature_column_names) for the
    Operator Twin: target is actual - planner-estimated time (personalization gap)."""
    df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    df[TARGET_COLUMN] = df["actual_time_min"] - df["estimated_time_min"]
    cols = feature_columns(df)
    return df, df[TARGET_COLUMN], cols
