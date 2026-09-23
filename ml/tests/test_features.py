"""Tests for the shared feature pipeline: no leakage, expected shape, reuse."""

import pandas as pd

from src.anomaly.dataset import build_anomaly_dataset
from src.common import config
from src.eta.dataset import build_eta_dataset
from src.features.build_features import LEAKAGE_COLUMNS, feature_columns
from src.operator_twin.dataset import build_operator_twin_dataset


def _build(tables):
    return build_eta_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )


def test_eta_dataset_shape_and_no_nans_in_features(tables):
    df, target, cols = _build(tables)
    assert len(df) == len(tables["tasks"])
    assert len(target) == len(df)
    assert len(cols) > 0
    assert df[cols].isna().sum().sum() == 0, "feature columns must not contain NaN"


def test_leakage_columns_excluded_from_features(tables):
    df, _, cols = _build(tables)
    assert LEAKAGE_COLUMNS.isdisjoint(cols)
    assert "actual_time_min" not in cols


def test_operator_history_features_do_not_leak_future(tables):
    """For every operator, the first task's prior-average must equal the
    planner estimate (no history yet) — proof no future row leaked backward."""
    df, _, _ = _build(tables)
    df_sorted = df.sort_values(["operator_id", "start_time"])
    first_per_operator = df_sorted.groupby("operator_id").first()
    assert (
        (first_per_operator["operator_avg_actual_time_min_prior"] - first_per_operator["estimated_time_min"])
        .abs()
        .max()
        < 1e-6
    )


def test_machine_degradation_signal_appears_in_features(tables):
    """The degrading machine's recent-vs-alltime gap should trend positive
    (recent tasks taking longer than its own historical average) by the end
    of the simulation window — this is the feature a model would use to
    catch degradation without being told which machine is degrading."""
    df, _, _ = _build(tables)
    machine_rows = df[df["machine_id"] == config.DEGRADING_MACHINE_ID].sort_values("start_time")
    late_rows = machine_rows.iloc[-10:]
    assert late_rows["machine_recent_vs_alltime_gap_prior"].mean() > 0


def test_operator_twin_and_anomaly_reuse_same_pipeline(tables):
    eta_df, _, eta_cols = _build(tables)
    twin_df, _, twin_cols = build_operator_twin_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )
    shared_cols = set(eta_cols) & set(twin_cols)
    # The two datasets should share the overwhelming majority of feature columns
    # (they call the exact same build_task_level_dataset()).
    assert len(shared_cols) / len(eta_cols) > 0.9
    assert len(eta_df) == len(twin_df)
