"""Tests for the realtime update path: `update_operator_state()` updates
only what a new telemetry reading can change, and never retrains anything."""

import pandas as pd

from src.common import config
from src.intelligence.operator_state import generate_operator_state
from src.intelligence.realtime import update_operator_state


def _initial_state():
    return generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)


def _next_real_row(state):
    telemetry_df = state["_context"]["tables"]["telemetry"]
    task_telemetry = telemetry_df[telemetry_df["task_id"] == config.DEMO_TASK_ID].sort_values("timestamp")
    return task_telemetry.iloc[0].to_dict()


def test_eta_updates_on_new_telemetry():
    state = _initial_state()
    row = _next_real_row(state)
    updated = update_operator_state(state, row)
    assert "dynamic_eta" in updated
    assert updated["remaining_work"]["buckets_completed"] >= state["remaining_work"]["buckets_completed"]


def test_risk_updates_from_new_row_fields():
    state = _initial_state()
    unsafe_row = {
        "timestamp": state["_context"]["task_row"]["start_time"],
        "machine_moving": True,
        "seatbelt_status": "unbuckled",
        "safety_alert": True,
        "load_cycles": 0,
        "idle_reason": None,
    }
    updated = update_operator_state(state, unsafe_row)
    assert updated["risk"]["risk_level"] == "critical"
    assert updated["risk"]["hard_rule_triggered"] == "seatbelt_unfastened_while_moving"


def test_focus_updates_with_new_timestamp():
    state = _initial_state()
    later_row = {
        "timestamp": state["_context"]["task_row"]["start_time"] + pd.Timedelta(hours=7),
        "machine_moving": True,
        "seatbelt_status": "buckled",
        "safety_alert": False,
        "load_cycles": 1,
        "idle_reason": None,
    }
    updated = update_operator_state(state, later_row)
    assert "score" in updated["focus"]
    assert 0 <= updated["focus"]["score"] <= 100


def test_habit_state_only_recomputes_on_a_real_transition():
    """A routine moving-row tick (not a truck-wait resume) must leave the
    habit summary exactly as it was — proving the update path doesn't
    needlessly rescan the whole fleet on every tick."""
    state = _initial_state()
    routine_row = {
        "timestamp": state["_context"]["task_row"]["start_time"],
        "machine_moving": True,
        "seatbelt_status": "buckled",
        "safety_alert": False,
        "load_cycles": 1,
        "idle_reason": None,
    }
    updated = update_operator_state(state, routine_row)
    assert updated["habits"][0] == state["habits"][0]


def test_no_model_retraining_uses_cached_bundle():
    """The ETA model object identity must be the SAME object across an
    update — proof nothing was refit."""
    state = _initial_state()
    row = _next_real_row(state)
    updated = update_operator_state(state, row)
    assert updated["_context"]["eta_bundle"] is state["_context"]["eta_bundle"]


def test_realtime_update_is_fast_enough_for_a_live_demo():
    """Not a strict benchmark — just a sanity ceiling that a single update
    doesn't do anything pathologically slow (like reloading all of
    data/synthetic/ from disk)."""
    import time

    state = _initial_state()
    row = _next_real_row(state)
    start = time.perf_counter()
    for _ in range(5):
        state = update_operator_state(state, row)
    elapsed = time.perf_counter() - start
    assert elapsed < 5.0


def test_sequential_updates_progress_remaining_work_downward():
    state = _initial_state()
    telemetry_df = state["_context"]["tables"]["telemetry"]
    task_telemetry = telemetry_df[telemetry_df["task_id"] == config.DEMO_TASK_ID].sort_values("timestamp")

    remaining_values = [state["remaining_work"]["buckets_remaining"]]
    for i in range(min(3, len(task_telemetry))):
        state = update_operator_state(state, task_telemetry.iloc[i].to_dict())
        remaining_values.append(state["remaining_work"]["buckets_remaining"])

    assert remaining_values == sorted(remaining_values, reverse=True)
