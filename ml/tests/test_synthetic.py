"""Tests for the synthetic data generator: determinism, demo IDs, planted patterns."""

import pandas as pd

from src.common import config
from src.common.synthetic import generate_all


def test_generation_is_deterministic():
    a = generate_all(seed=config.SEED)
    b = generate_all(seed=config.SEED)
    pd.testing.assert_frame_equal(a["tasks"], b["tasks"])
    pd.testing.assert_frame_equal(a["telemetry"], b["telemetry"])


def test_all_tables_non_empty(tables):
    for name, df in tables.items():
        assert len(df) > 0, f"{name} table is empty"


def test_demo_identifiers_exist(tables):
    operators, machines, tasks = tables["operators"], tables["machines"], tables["tasks"]
    assert (operators["operator_id"] == config.DEMO_OPERATOR_ID).any()
    assert (machines["machine_id"] == config.DEMO_MACHINE_ID).any()
    demo_task = tasks[tasks["task_id"] == config.DEMO_TASK_ID]
    assert len(demo_task) == 1
    assert demo_task.iloc[0]["operator_id"] == config.DEMO_OPERATOR_ID
    assert demo_task.iloc[0]["machine_id"] == config.DEMO_MACHINE_ID


def test_entity_relationships_are_valid(tables):
    operator_ids = set(tables["operators"]["operator_id"])
    machine_ids = set(tables["machines"]["machine_id"])
    task_ids = set(tables["tasks"]["task_id"])

    assert set(tables["tasks"]["operator_id"]) <= operator_ids
    assert set(tables["tasks"]["machine_id"]) <= machine_ids
    assert set(tables["telemetry"]["operator_id"]) <= operator_ids
    assert set(tables["telemetry"]["machine_id"]) <= machine_ids
    assert set(tables["telemetry"]["task_id"]) <= task_ids


def test_no_negative_values(tables):
    telemetry = tables["telemetry"]
    assert (telemetry["fuel_used_l"] >= 0).all()
    assert (telemetry["load_cycles"] >= 0).all()
    assert (telemetry["idling_time_min"] >= 0).all()
    tasks = tables["tasks"]
    assert (tasks["actual_time_min"] > 0).all()
    assert (tasks["volume_m3"] > 0).all()


def test_planted_patterns_present(tables):
    task_gt = tables["task_ground_truth"]
    assert task_gt["is_afternoon_slowdown"].any()
    assert task_gt["is_legitimate_idle_dominant"].any()
    assert task_gt["is_degrading_machine_task"].any()
    assert task_gt["is_inefficient_operator_task"].any()
    assert task_gt["is_seatbelt_habit_operator_task"].any()

    near_misses = tables["near_misses"]
    assert len(near_misses) > 0
    assert (near_misses["distance_m"] <= config.SWING_ZONE_RADIUS_M).all()


def test_ground_truth_labels_cover_every_planted_pattern(tables):
    labels = tables["ground_truth_labels"]
    expected = {
        "seatbelt_habit",
        "afternoon_slowdown",
        "machine_degradation",
        "operator_inefficiency",
        "legitimate_idle",
        "proximity_near_miss",
    }
    assert expected <= set(labels["pattern_type"])


def test_machine_degradation_trend(tables):
    """The planted machine's average cycle time should trend up over the
    simulation window more than a normal machine's."""
    telemetry = tables["telemetry"]
    moving = telemetry[telemetry["machine_moving"]]

    def _trend(machine_id: str) -> float:
        sub = moving[moving["machine_id"] == machine_id].sort_values("timestamp")
        if len(sub) < 20:
            return 0.0
        first_half = sub.iloc[: len(sub) // 2]["avg_cycle_time_s"].mean()
        second_half = sub.iloc[len(sub) // 2 :]["avg_cycle_time_s"].mean()
        return second_half - first_half

    degrading_trend = _trend(config.DEGRADING_MACHINE_ID)
    other_machine = [m for m in tables["machines"]["machine_id"] if m != config.DEGRADING_MACHINE_ID][0]
    normal_trend = _trend(other_machine)

    assert degrading_trend > normal_trend
