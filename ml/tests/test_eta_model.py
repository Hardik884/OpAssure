"""Tests for ETA model training, selection, and point/interval inference."""

import sys

import pandas as pd

from src.common import config
from src.eta.dataset import build_eta_dataset
from src.eta.inference import predict_eta, predict_personalized_eta
from src.evaluation.splits import time_aware_split


def _build(tables):
    return build_eta_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )


def test_training_compares_at_least_two_candidates(eta_report):
    assert len(eta_report["candidates"]) >= 2
    assert eta_report["selected_model"] in eta_report["candidates"]


def test_training_reports_mae_rmse_median_ae(eta_report):
    best = eta_report["candidates"][eta_report["selected_model"]]
    for split in ("val", "test"):
        for metric in ("mae", "rmse", "median_ae"):
            assert metric in best[split]
            assert best[split][metric] >= 0


def test_selection_uses_time_aware_split_not_random(tables, eta_report):
    """The split sizes reported by training must match time_aware_split's
    output exactly — proof training didn't quietly shuffle the data."""
    features_df, _, _ = _build(tables)
    train_df, val_df, test_df = time_aware_split(features_df)
    assert eta_report["split_sizes"] == {"train": len(train_df), "val": len(val_df), "test": len(test_df)}


def test_best_model_selected_by_lowest_val_mae(eta_report):
    best_mae = eta_report["candidates"][eta_report["selected_model"]]["val"]["mae"]
    for name, scores in eta_report["candidates"].items():
        assert scores["val"]["mae"] >= best_mae - 1e-9


def test_predict_eta_returns_a_float(tables, eta_bundle):
    features_df, _, _ = _build(tables)
    row = features_df.iloc[0]
    pred = predict_eta(row, eta_bundle)
    assert isinstance(pred, float)
    assert pred > 0


def test_predict_eta_matches_demo_task(tables, eta_bundle):
    features_df, _, _ = _build(tables)
    demo_row = features_df[features_df["task_id"] == config.DEMO_TASK_ID].iloc[0]
    pred = predict_eta(demo_row, eta_bundle)
    assert pred > 0


def test_personalized_eta_range_is_sane(tables, eta_bundle):
    features_df, _, _ = _build(tables)
    row = features_df.iloc[0]
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    result = predict_personalized_eta(row, twin, telemetry_so_far=None, model_bundle=eta_bundle)

    for key in ("eta_min", "eta_max", "eta_point", "original_eta", "reason", "buckets_remaining"):
        assert key in result

    assert result["eta_min"] <= result["eta_point"] <= result["eta_max"]
    assert result["eta_min"] >= 1.0  # never a non-positive ETA
    assert isinstance(result["reason"], str) and len(result["reason"]) > 0
    assert result["buckets_remaining"] == int(row["estimated_buckets"])


def test_personalized_eta_is_never_a_fake_single_point(tables, eta_bundle):
    """The interval must actually have width — not eta_min == eta_max, which
    would just be a point estimate wearing a disguise."""
    features_df, _, _ = _build(tables)
    row = features_df.iloc[0]
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    result = predict_personalized_eta(row, twin, model_bundle=eta_bundle)
    assert result["eta_max"] > result["eta_min"]


def test_fast_vs_slow_task_produce_different_personalized_eta(tables, eta_bundle):
    """Sanity check: two different tasks should not always get the exact
    same personalized prediction (the model must actually be using the
    per-task features, not returning a constant)."""
    features_df, _, _ = _build(tables)
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    preds = [
        predict_personalized_eta(features_df.iloc[i], twin, model_bundle=eta_bundle)["eta_point"]
        for i in range(10)
    ]
    assert len(set(preds)) > 1


def test_eta_point_stays_within_its_own_range_for_extreme_inputs(tables, eta_bundle):
    """Regression test (production audit): an out-of-distribution row
    (near-zero estimated buckets/volume and zero historical aggregates) used
    to make the raw linear-model prediction go negative, while eta_min/eta_max
    were independently clamped — producing eta_point OUTSIDE [eta_min,
    eta_max] and even negative. predict_eta() now floors the raw prediction,
    and predict_personalized_eta() clamps eta_point into its own range as a
    second line of defense regardless of quantile sign."""
    features_df, _, _ = _build(tables)
    row = features_df.iloc[0].copy()
    row["estimated_buckets"] = 0
    row["volume_m3"] = 0.001
    row["operator_avg_actual_time_min_prior"] = 0
    row["machine_avg_actual_time_min_prior"] = 0
    row["operator_tasks_completed_prior"] = 0

    point = predict_eta(row, eta_bundle)
    assert point >= 1.0  # MIN_ETA_MIN floor — never negative or zero

    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    result = predict_personalized_eta(row, twin, model_bundle=eta_bundle)
    assert result["eta_min"] <= result["eta_point"] <= result["eta_max"]
    assert result["eta_min"] >= 0


def test_model_io_does_not_import_the_training_module():
    """Regression test (production audit): model_io.py (the pure inference/
    loading path) previously imported MODEL_PATH/METADATA_PATH from train.py,
    coupling every inference-only caller to the training module's sklearn
    fitting imports. Both now source these paths from config.py independently."""
    for mod in ("src.eta.model_io", "src.eta.train"):
        sys.modules.pop(mod, None)

    import src.eta.model_io as model_io_module

    assert "src.eta.train" not in sys.modules, (
        "importing src.eta.model_io pulled in src.eta.train — the inference "
        "path should not depend on the training module."
    )
    assert model_io_module.MODEL_PATH == config.ETA_MODEL_PATH
    assert model_io_module.METADATA_PATH == config.ETA_METADATA_PATH
