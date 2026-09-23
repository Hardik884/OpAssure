"""Tests for Just-in-Time Micro Training: recommendation, effectiveness
tracking, and instructor escalation."""

import pandas as pd

from src.common import config
from src.training.effectiveness import evaluate_training_effect
from src.training.escalation import check_escalation
from src.training.recommend import get_training_recommendation, recommend_training


def test_recommendation_triggers_for_a_real_habit():
    habit = {"is_habit": True, "count": 5, "opportunities": 12}
    result = recommend_training(habit_summary=habit)
    assert result["recommended"] is True
    assert result["trigger_type"] == "seatbelt_habit"
    assert result["clip_id"] == "TR_SEATBELT_TRUCKWAIT"
    assert result["safe_timing"] == "truck_wait"


def test_no_recommendation_for_weak_evidence():
    """A non-habit (is_habit False) and everything else below threshold
    should never trigger a recommendation."""
    habit = {"is_habit": False, "count": 1, "opportunities": 20}
    result = recommend_training(habit_summary=habit, proximity_event_count=1)
    assert result["recommended"] is False


def test_no_recommendation_when_nothing_is_passed():
    result = recommend_training()
    assert result["recommended"] is False


def test_correct_clip_mapping_for_proximity():
    result = recommend_training(proximity_event_count=config.TRAINING_MIN_PROXIMITY_EVENTS)
    assert result["recommended"] is True
    assert result["clip_id"] == "TR_SWING_ZONE"
    assert result["trigger_type"] == "proximity_event"


def test_correct_clip_mapping_for_fuel_inefficiency():
    finding = {"source": "operator", "operator_id": "OPX", "n_distinct_entities": 5, "ratio_vs_fleet": 1.3}
    result = recommend_training(fuel_finding=finding)
    assert result["recommended"] is True
    assert result["clip_id"] == "TR_IDLE_EFFICIENCY"
    assert result["trigger_type"] == "fuel_inefficiency"


def test_correct_clip_mapping_for_wet_weather_and_heat():
    wet_twin = {"nTasks": 20, "rainSensitivity": 0.25, "heatSensitivity": 0.0}
    wet_result = recommend_training(operator_twin=wet_twin)
    assert wet_result["clip_id"] == "TR_WET_TRENCHING"

    hot_twin = {"nTasks": 20, "rainSensitivity": 0.0, "heatSensitivity": 0.25}
    hot_result = recommend_training(operator_twin=hot_twin)
    assert hot_result["clip_id"] == "TR_HEAT_SAFETY"


def test_sensitivity_trigger_requires_enough_history():
    """A high sensitivity from only a couple of tasks must NOT trigger —
    not enough evidence yet."""
    sparse_twin = {"nTasks": 2, "rainSensitivity": 0.9, "heatSensitivity": 0.0}
    result = recommend_training(operator_twin=sparse_twin)
    assert result["recommended"] is False


def test_priority_order_prefers_safety_over_efficiency():
    habit = {"is_habit": True, "count": 5, "opportunities": 12}
    finding = {"source": "operator", "operator_id": "OPX", "n_distinct_entities": 5, "ratio_vs_fleet": 1.3}
    result = recommend_training(habit_summary=habit, fuel_finding=finding, proximity_event_count=10)
    assert result["trigger_type"] == "seatbelt_habit"


def test_real_data_recommendation_for_planted_operators(tables):
    result = get_training_recommendation(
        config.SEATBELT_HABIT_OPERATOR_ID, tables["tasks"], tables["telemetry"], tables["operators"], tables["near_misses"]
    )
    assert result["recommended"] is True


# --- Training effectiveness --------------------------------------------------


def _seatbelt_tasks(operator_id: str, n: int, start: pd.Timestamp, unsafe: bool):
    """Build minimal tasks+telemetry that make _seatbelt_series() detect `n`
    truck-wait opportunities, each either always-unsafe or always-safe."""
    tasks_rows, telemetry_rows = [], []
    for i in range(n):
        task_id = f"T{operator_id}_{start.value}_{i}"
        ts = start + pd.Timedelta(hours=i)
        tasks_rows.append(
            {
                "task_id": task_id,
                "operator_id": operator_id,
                "start_time": ts,
                "estimated_time_min": 30,
                "actual_time_min": 30,
                "weather": "clear",
            }
        )
        telemetry_rows.append(
            {
                "task_id": task_id,
                "operator_id": operator_id,
                "timestamp": ts,
                "machine_moving": False,
                "idle_reason": "waiting_for_truck",
                "seatbelt_status": "unbuckled" if unsafe else "buckled",
            }
        )
        telemetry_rows.append(
            {
                "task_id": task_id,
                "operator_id": operator_id,
                "timestamp": ts + pd.Timedelta(minutes=5),
                "machine_moving": True,
                "idle_reason": None,
                "seatbelt_status": "unbuckled" if unsafe else "buckled",
            }
        )
    return pd.DataFrame(tasks_rows), pd.DataFrame(telemetry_rows)


def test_incomplete_five_task_window_does_not_fabricate():
    before_tasks, before_telemetry = _seatbelt_tasks("OPX", 5, pd.Timestamp("2026-06-01"), unsafe=True)
    after_tasks, after_telemetry = _seatbelt_tasks("OPX", 2, pd.Timestamp("2026-06-05"), unsafe=False)  # only 2, not 5
    tasks_df = pd.concat([before_tasks, after_tasks], ignore_index=True)
    telemetry_df = pd.concat([before_telemetry, after_telemetry], ignore_index=True)

    result = evaluate_training_effect("OPX", "seatbelt", pd.Timestamp("2026-06-03"), tasks_df, telemetry_df)
    assert result["observations"] == 2
    assert result["status"] == "insufficient_evidence"
    assert result["improvement"] is None
    assert "note" in result


def test_improving_status_when_behaviour_gets_better():
    before_tasks, before_telemetry = _seatbelt_tasks("OPX", 5, pd.Timestamp("2026-06-01"), unsafe=True)
    after_tasks, after_telemetry = _seatbelt_tasks("OPX", 5, pd.Timestamp("2026-06-05"), unsafe=False)
    tasks_df = pd.concat([before_tasks, after_tasks], ignore_index=True)
    telemetry_df = pd.concat([before_telemetry, after_telemetry], ignore_index=True)

    result = evaluate_training_effect("OPX", "seatbelt", pd.Timestamp("2026-06-03"), tasks_df, telemetry_df)
    assert result["observations"] == 5
    assert result["before"] == 1.0
    assert result["after"] == 0.0
    assert result["improvement"] == 1.0
    assert result["status"] == "improving"


def test_no_improvement_status_when_behaviour_unchanged():
    before_tasks, before_telemetry = _seatbelt_tasks("OPX", 5, pd.Timestamp("2026-06-01"), unsafe=True)
    after_tasks, after_telemetry = _seatbelt_tasks("OPX", 5, pd.Timestamp("2026-06-05"), unsafe=True)
    tasks_df = pd.concat([before_tasks, after_tasks], ignore_index=True)
    telemetry_df = pd.concat([before_telemetry, after_telemetry], ignore_index=True)

    result = evaluate_training_effect("OPX", "seatbelt", pd.Timestamp("2026-06-03"), tasks_df, telemetry_df)
    assert result["status"] == "no_change"


def test_real_data_effectiveness_across_all_planted_checkpoints(tables):
    """Sanity check against the real generated dataset: at least one
    checkpoint should reach a full 5-observation window with a definitive
    status (not every checkpoint is doomed to insufficient evidence)."""
    training_events = tables["training_events"]
    op_events = training_events[training_events["operator_id"] == config.SEATBELT_HABIT_OPERATOR_ID]
    assert len(op_events) > 0

    statuses = [
        evaluate_training_effect(
            config.SEATBELT_HABIT_OPERATOR_ID, "seatbelt", row["timestamp"], tables["tasks"], tables["telemetry"]
        )["status"]
        for _, row in op_events.iterrows()
    ]
    assert "improving" in statuses or "worsening" in statuses or "no_change" in statuses


# --- Instructor escalation ---------------------------------------------------


def test_escalation_on_no_improvement():
    result = check_escalation({"status": "no_change", "observations": 5, "metric_type": "seatbelt"})
    assert result["escalate"] is True
    assert result["recommended_session_minutes"] == config.ESCALATION_SESSION_MINUTES


def test_escalation_on_worsening():
    result = check_escalation({"status": "worsening", "observations": 5, "metric_type": "seatbelt"})
    assert result["escalate"] is True


def test_no_escalation_on_improvement():
    result = check_escalation({"status": "improving", "observations": 5, "metric_type": "seatbelt"})
    assert result["escalate"] is False


def test_no_escalation_on_insufficient_evidence():
    """A single incomplete window must never trigger escalation — the
    system should not punish an operator before there's enough data."""
    result = check_escalation({"status": "insufficient_evidence", "observations": 2})
    assert result["escalate"] is False
