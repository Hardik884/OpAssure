"""Tests for Idle Shield: legitimate/avoidable classification and the
hard no-blame guarantee for truck-wait idle."""

import pandas as pd

from src.anomaly.idle_shield import classify_idle, classify_task_idle
from src.common import config
from src.evaluation.behaviour_eval import evaluate_idle_shield


def test_truck_waiting_is_legitimate():
    result = classify_idle({"idle_reason": "waiting_for_truck"})
    assert result["idle_type"] == "legitimate"
    assert result["confidence"] > 0.5


def test_break_is_legitimate():
    result = classify_idle({"idle_reason": "break"})
    assert result["idle_type"] == "legitimate"


def test_waiting_for_instruction_is_legitimate():
    result = classify_idle({"idle_reason": "waiting_for_instruction"})
    assert result["idle_type"] == "legitimate"


def test_unnecessary_idle_is_avoidable():
    result = classify_idle({"idle_reason": "unnecessary"})
    assert result["idle_type"] == "avoidable"
    assert result["confidence"] > 0.5


def test_unrecognized_reason_is_conservative_low_confidence():
    result = classify_idle({"idle_reason": "something_unexpected"})
    assert result["idle_type"] == "avoidable"
    assert result["confidence"] < 0.5


def test_no_blame_guarantee_holds_for_every_idle_reason_variant():
    """Hard, unconditional rule: waiting_for_truck (or any configured
    legitimate reason) can NEVER come out "avoidable", regardless of any
    other field on the row."""
    for reason in config.LEGITIMATE_IDLE_REASONS:
        for extra in ({}, {"task_type": "loading"}, {"idling_time_min": 999}, {"idling_time_min": 0.1}):
            row = {"idle_reason": reason, **extra}
            assert classify_idle(row)["idle_type"] == "legitimate"


def test_classify_task_idle_never_blames_a_truck_dependent_task(tables):
    """Every real truck-wait idle block in the generated dataset must
    classify as legitimate at the row level — never avoidable."""
    idle_rows = tables["telemetry"][
        (tables["telemetry"]["idling_time_min"] > 0) & (tables["telemetry"]["idle_reason"] == "waiting_for_truck")
    ]
    for _, row in idle_rows.sample(n=min(500, len(idle_rows)), random_state=config.SEED).iterrows():
        assert classify_idle(row)["idle_type"] == "legitimate"


def test_ground_truth_evaluation_reports_zero_false_blame(tables):
    report = evaluate_idle_shield(tables["telemetry"], tables["task_ground_truth"])
    assert report["legitimate_idle_falsely_blamed_count"] == 0
    assert report["legitimate_idle_falsely_blamed_rate"] == 0.0
    assert report["truck_wait_tasks_evaluated"] > 0


def test_ground_truth_evaluation_reports_precision_recall(tables):
    report = evaluate_idle_shield(tables["telemetry"], tables["task_ground_truth"])
    for metric in ("accuracy", "precision", "recall", "f1", "false_positive_rate"):
        assert metric in report
        assert 0.0 <= report[metric] <= 1.0
