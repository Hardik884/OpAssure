"""ETA (task time estimation) dataset.

Thin wrapper around the shared feature pipeline: selects `actual_time_min`
(actual task duration) as the regression target. No model is trained here —
this step only produces `(X, y)` ready for a future model.
"""

import pandas as pd

from src.features.build_features import build_task_level_dataset, feature_columns

TARGET_COLUMN = "actual_time_min"


def build_eta_dataset(
    tasks_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.Series, list[str]]:
    """Return (full_feature_df, target_series, feature_column_names) for ETA."""
    df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    cols = feature_columns(df)
    return df, df[TARGET_COLUMN], cols
