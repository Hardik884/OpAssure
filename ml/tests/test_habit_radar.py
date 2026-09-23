"""Tests for Habit Radar: repeated-pattern detection, the "not a single
event" guarantee, and frequency calculation."""

import pandas as pd

from src.anomaly.habit_radar import detect_habits, get_habit_summary
from src.common import config


def _base_row(**overrides):
    row = {
        "task_id": "T1",
        "operator_id": "OPX",
        "timestamp": pd.Timestamp("2026-06-01 08:00:00"),
        "machine_moving": False,
        "idle_reason": "waiting_for_truck",
        "seatbelt_status": "buckled",
    }
    row.update(overrides)
    return row


def _build_opportunity_rows(task_id: str, operator_id: str, unbuckled_idle: bool, unbuckled_resume: bool):
    """One idle row followed by one moving row = one opportunity."""
    idle = _base_row(
        task_id=task_id,
        operator_id=operator_id,
        timestamp=pd.Timestamp("2026-06-01 08:00:00"),
        machine_moving=False,
        seatbelt_status="unbuckled" if unbuckled_idle else "buckled",
    )
    move = _base_row(
        task_id=task_id,
        operator_id=operator_id,
        timestamp=pd.Timestamp("2026-06-01 08:05:00"),
        machine_moving=True,
        idle_reason=None,
        seatbelt_status="unbuckled" if unbuckled_resume else "buckled",
    )
    return [idle, move]


def test_repeated_habit_is_detected():
    """One operator with the unsafe pattern on 4 of 4 opportunities, vs. a
    fleet of operators with zero occurrences, should be flagged."""
    rows = []
    for i in range(4):
        rows += _build_opportunity_rows(f"Thab{i}", "OP_HABIT", unbuckled_idle=True, unbuckled_resume=True)
    # A fleet of "normal" operators, each with several opportunities (so
    # they clear the same min_opportunities floor) but zero occurrences —
    # enough of them that the one outlier doesn't dominate the pooled
    # fleet mean/std it's being compared against (mirrors the real ~20
    # operator fleet, where one habitual operator is a small fraction).
    for i in range(10):
        op = f"OP_NORMAL{i}"
        for j in range(4):
            rows += _build_opportunity_rows(f"T{op}_{j}", op, unbuckled_idle=False, unbuckled_resume=False)

    telemetry_df = pd.DataFrame(rows)
    results = detect_habits(telemetry_df)
    habit_row = next(r for r in results if r["operator_id"] == "OP_HABIT")

    assert habit_row["count"] == 4
    assert habit_row["opportunities"] == 4
    assert habit_row["is_habit"] is True


def test_single_event_is_not_a_habit():
    """A single occurrence must never be flagged, however extreme it looks."""
    rows = _build_opportunity_rows("T1", "OP_SINGLE", unbuckled_idle=True, unbuckled_resume=True)
    # Give this operator a couple more opportunities where nothing happens,
    # so we're testing "1 unsafe event out of several opportunities", not
    # just "not enough opportunities to say anything at all".
    rows += _build_opportunity_rows("T2", "OP_SINGLE", unbuckled_idle=False, unbuckled_resume=False)
    rows += _build_opportunity_rows("T3", "OP_SINGLE", unbuckled_idle=False, unbuckled_resume=False)

    telemetry_df = pd.DataFrame(rows)
    result = get_habit_summary("OP_SINGLE", telemetry_df)

    assert result["count"] == 1
    assert result["is_habit"] is False


def test_frequency_calculation_is_correct():
    rows = []
    for i in range(3):
        rows += _build_opportunity_rows(f"Ta{i}", "OP_X", unbuckled_idle=True, unbuckled_resume=True)
    for i in range(7):
        rows += _build_opportunity_rows(f"Tb{i}", "OP_X", unbuckled_idle=False, unbuckled_resume=False)

    telemetry_df = pd.DataFrame(rows)
    result = get_habit_summary("OP_X", telemetry_df)

    assert result["opportunities"] == 10
    assert result["count"] == 3
    assert result["frequency"] == 0.3


def test_no_opportunities_returns_safe_default():
    telemetry_df = pd.DataFrame(
        [_base_row(task_id="T1", operator_id="OP_OTHER", machine_moving=True, idle_reason=None)]
    )
    result = get_habit_summary("OP_NEVER_IDLE", telemetry_df)
    assert result["opportunities"] == 0
    assert result["is_habit"] is False


def test_real_synthetic_data_flags_exactly_the_planted_operator(tables):
    """End-to-end sanity check against the real generated dataset — the only
    operator flagged should be the one the generator actually planted the
    habit on."""
    results = detect_habits(tables["telemetry"])
    flagged = {r["operator_id"] for r in results if r["is_habit"]}
    assert config.SEATBELT_HABIT_OPERATOR_ID in flagged
