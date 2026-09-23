"""Tests for remaining-work calculation, the dynamic ETA update, and the
structured explanation module."""

import pandas as pd

from src.common import config
from src.eta.dataset import build_eta_dataset
from src.eta.dynamic import predict_dynamic_eta
from src.eta.explain import build_eta_explanation
from src.eta.remaining_work import calculate_remaining_work
from src.operator_twin.twin import get_operator_profile


def _demo_task_features(tables):
    features_df, _, _ = build_eta_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )
    return features_df[features_df["task_id"] == config.DEMO_TASK_ID].iloc[0]


def test_remaining_work_before_task_starts(tables):
    task_features = _demo_task_features(tables)
    result = calculate_remaining_work(task_features, telemetry_so_far=None)
    assert result["buckets_completed"] == 0
    assert result["buckets_remaining"] == int(task_features["estimated_buckets"])
    assert result["pct_complete"] == 0.0
    assert result["trucks_remaining"] is None  # never fabricated


def test_remaining_work_partway_through(tables):
    task_features = _demo_task_features(tables)
    task_telemetry = tables["telemetry"][tables["telemetry"]["task_id"] == config.DEMO_TASK_ID].sort_values(
        "timestamp"
    )
    halfway = task_telemetry.iloc[: max(1, len(task_telemetry) // 2)]

    result = calculate_remaining_work(task_features, halfway)
    assert result["buckets_completed"] == int(halfway["load_cycles"].sum())
    assert result["buckets_remaining"] == max(0, result["total_buckets"] - result["buckets_completed"])
    assert 0.0 <= result["pct_complete"] <= 1.0


def test_remaining_work_does_not_invent_truck_counts(tables):
    task_features = _demo_task_features(tables)
    result = calculate_remaining_work(task_features, telemetry_so_far=None)
    assert result["trucks_remaining"] is None


def test_dynamic_eta_update_returns_sane_interval(tables, eta_bundle):
    task_features = _demo_task_features(tables)
    task_telemetry = tables["telemetry"][tables["telemetry"]["task_id"] == config.DEMO_TASK_ID].sort_values(
        "timestamp"
    )
    telemetry_so_far = task_telemetry.iloc[: max(1, len(task_telemetry) // 2)]
    twin = get_operator_profile(config.DEMO_OPERATOR_ID, tables["tasks"], tables["telemetry"], tables["operators"])

    result = predict_dynamic_eta(task_features, telemetry_so_far, twin, model_bundle=eta_bundle)

    assert result["eta_min"] <= result["eta_point"] <= result["eta_max"]
    assert result["buckets_remaining"] >= 0
    assert 0.0 <= result["pct_complete"] <= 1.0
    assert isinstance(result["reason"], str) and len(result["reason"]) > 0


def test_dynamic_eta_detects_cycle_time_increase(tables, eta_bundle):
    """Construct synthetic telemetry with a deliberately slow recent cycle
    time and confirm the reported cycle_time_change_pct is positive
    (running slower than plan) and reflected in the reason text."""
    task_features = _demo_task_features(tables)
    original_point = 60.0  # pretend a round-number original estimate
    total_buckets = int(task_features["estimated_buckets"])
    planned_cycle_time_s = (original_point * 60.0) / total_buckets

    slow_telemetry = pd.DataFrame(
        {
            "timestamp": pd.date_range(task_features["start_time"], periods=3, freq="5min"),
            "machine_moving": [True, True, True],
            "load_cycles": [2, 2, 2],
            "avg_cycle_time_s": [planned_cycle_time_s * 1.5] * 3,  # 50% slower than planned
        }
    )
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}

    result = predict_dynamic_eta(
        task_features, slow_telemetry, twin, original_point_eta_min=original_point, model_bundle=eta_bundle
    )
    assert result["cycle_time_change_pct"] > 0.1
    assert "cycle time" in result["reason"].lower()


def test_dynamic_eta_uncertainty_shrinks_near_completion(tables, eta_bundle):
    """The interval width should be smaller when a task is nearly done than
    when it has barely started, since less remaining work means less that
    can still deviate from the estimate."""
    task_features = _demo_task_features(tables)
    total_buckets = int(task_features["estimated_buckets"])
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}

    barely_started = pd.DataFrame(
        {
            "timestamp": [task_features["start_time"]],
            "machine_moving": [True],
            "load_cycles": [1],
            "avg_cycle_time_s": [30.0],
        }
    )
    nearly_done = pd.DataFrame(
        {
            "timestamp": [task_features["start_time"]],
            "machine_moving": [True],
            "load_cycles": [max(1, total_buckets - 1)],
            "avg_cycle_time_s": [30.0],
        }
    )

    early_result = predict_dynamic_eta(task_features, barely_started, twin, original_point_eta_min=60.0, model_bundle=eta_bundle)
    late_result = predict_dynamic_eta(task_features, nearly_done, twin, original_point_eta_min=60.0, model_bundle=eta_bundle)

    early_width = early_result["eta_max"] - early_result["eta_min"]
    late_width = late_result["eta_max"] - late_result["eta_min"]
    assert late_width <= early_width


def test_explanation_flags_rain_as_negative():
    task_row = {"weather": "rain", "machine_age": 3, "hour_of_day": 9}
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    explanation = build_eta_explanation(task_row, twin)
    weather_factor = next(f for f in explanation["factors"] if f["name"] == "weather")
    assert weather_factor["impact"] == "negative"


def test_explanation_flags_old_machine_as_negative():
    task_row = {"weather": "clear", "machine_age": 10, "hour_of_day": 9}
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    explanation = build_eta_explanation(task_row, twin)
    age_factor = next(f for f in explanation["factors"] if f["name"] == "machine_age")
    assert age_factor["impact"] == "negative"


def test_explanation_flags_fast_operator_as_positive():
    task_row = {"weather": "clear", "machine_age": 3, "hour_of_day": 9}
    twin = {"paceFactor": 1.15, "afternoonEffect": 0.0}
    explanation = build_eta_explanation(task_row, twin)
    pace_factor = next(f for f in explanation["factors"] if f["name"] == "operator_pace")
    assert pace_factor["impact"] == "positive"


def test_explanation_reason_is_never_empty():
    task_row = {"weather": "clear", "machine_age": 3, "hour_of_day": 9}
    twin = {"paceFactor": 1.0, "afternoonEffect": 0.0}
    explanation = build_eta_explanation(task_row, twin)
    assert isinstance(explanation["reason"], str) and len(explanation["reason"]) > 0
