"""Anomaly / unusual-behaviour dataset.

Reuses the shared task-level feature pipeline. Ground truth for planted
anomalies lives in `data/ground_truth/task_ground_truth.csv` — this module
just joins that onto the feature matrix so classifiers can be trained and
evaluated against it (see `/ml-evaluation`).
"""

import pandas as pd

from src.common.loaders import load_task_ground_truth
from src.features.build_features import build_task_level_dataset, feature_columns

LABEL_COLUMNS = [
    "is_afternoon_slowdown",
    "is_legitimate_idle_dominant",
    "is_degrading_machine_task",
    "is_inefficient_operator_task",
    "is_seatbelt_habit_operator_task",
    "has_near_miss",
]


def build_anomaly_dataset(
    tasks_df: pd.DataFrame,
    operators_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    weather_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame, list[str]]:
    """Return (full_feature_df, labels_df, feature_column_names).

    `labels_df` has one boolean column per planted pattern from
    `task_ground_truth.csv`, aligned by `task_id`.
    """
    df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    labels = load_task_ground_truth()
    df = df.merge(labels, on="task_id", how="left")
    cols = feature_columns(df)
    return df, df[["task_id"] + LABEL_COLUMNS], cols
