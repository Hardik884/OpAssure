"""Tests for the Operator Twin: shape, shrinkage, fleet-average fallback,
data-driven pace direction, and the leakage guarantee of the `as_of` cutoff.
"""

import pandas as pd
import pytest

from src.common import config
from src.operator_twin.twin import _shrink, build_operator_twin, get_operator_profile


def test_twin_has_one_row_per_operator_with_history(tables):
    twin_df = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"])
    assert set(twin_df["operator_id"]) == set(tables["operators"]["operator_id"])
    for col in ("pace_factor", "rain_sensitivity", "heat_sensitivity", "afternoon_effect", "fuel_efficiency"):
        assert col in twin_df.columns
        assert twin_df[col].notna().all()


def test_demo_operator_profile_matches_camel_case_contract(tables):
    profile = get_operator_profile(config.DEMO_OPERATOR_ID, tables["tasks"], tables["telemetry"], tables["operators"])
    expected_keys = {
        "operatorId",
        "paceFactor",
        "rainSensitivity",
        "heatSensitivity",
        "afternoonEffect",
        "fuelEfficiency",
        "seatbeltViolationRate",
        "nTasks",
    }
    assert expected_keys <= set(profile.keys())
    assert profile["operatorId"] == config.DEMO_OPERATOR_ID
    assert profile["nTasks"] > 0


def test_fleet_average_fallback_for_operator_with_no_history(tables):
    """An as_of cutoff before ANY task exists should fall back to fleet-neutral
    defaults instead of crashing or returning garbage."""
    very_early = pd.Timestamp(config.SIM_START_DATE)  # before the first task even starts
    profile = get_operator_profile(
        config.DEMO_OPERATOR_ID, tables["tasks"], tables["telemetry"], tables["operators"], as_of=very_early
    )
    assert profile["nTasks"] == 0
    assert profile["paceFactor"] == 1.0


def test_shrink_formula_is_a_weighted_blend_toward_fleet_value():
    """Whitebox check of the shrinkage math itself: weight = n / (n + k).
    Deterministic, so it doesn't depend on which two tasks a real operator's
    early (noisy) history happens to contain."""
    n, k = 2, 5
    result = _shrink(operator_value=2.0, fleet_value=1.0, n=n, k=k)
    expected_weight = n / (n + k)
    expected = expected_weight * 2.0 + (1 - expected_weight) * 1.0
    assert result == pytest.approx(expected)
    # With only n=2 against k=5, the fleet value should dominate: shrunk
    # result stays closer to the fleet value (1.0) than to the raw one (2.0).
    assert abs(result - 1.0) < abs(2.0 - 1.0)


def test_shrink_approaches_operator_value_as_history_grows():
    """As n grows relative to k, the shrunk estimate should move steadily
    closer to the operator's own (raw) value."""
    far = _shrink(operator_value=2.0, fleet_value=1.0, n=2, k=5)
    close = _shrink(operator_value=2.0, fleet_value=1.0, n=200, k=5)
    assert abs(close - 2.0) < abs(far - 2.0)


def test_sparse_history_has_fewer_tasks_and_stays_within_a_sane_range(tables):
    """An operator with only their first couple of tasks should still
    produce a bounded, sane pace_factor (shrinkage keeps a 2-task noisy
    sample from producing an absurd value) even though it won't necessarily
    land as close to 1.0 as a 165-task estimate — see the two tests above
    for the actual shrinkage-math guarantee."""
    tasks = tables["tasks"].sort_values("start_time")
    demo_tasks = tasks[tasks["operator_id"] == config.DEMO_OPERATOR_ID]
    early_cutoff = demo_tasks.iloc[2]["start_time"]  # right after their 2nd task

    sparse_twin = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"], as_of=early_cutoff)
    full_twin = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"])

    sparse_row = sparse_twin[sparse_twin["operator_id"] == config.DEMO_OPERATOR_ID].iloc[0]
    full_row = full_twin[full_twin["operator_id"] == config.DEMO_OPERATOR_ID].iloc[0]

    assert sparse_row["n_tasks"] < full_row["n_tasks"]
    assert 0.2 < sparse_row["pace_factor"] < 5.0


def test_expert_operators_are_not_slower_than_novice_on_average(tables):
    """Data-driven sanity check (not a hardcoded expectation of exact
    numbers): experts shouldn't come out systematically *slower* than
    novices in the fleet's own duration-ratio data."""
    twin_df = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"])
    merged = twin_df.merge(tables["operators"][["operator_id", "skill"]], on="operator_id")
    by_skill = merged.groupby("skill")["pace_factor"].mean()
    if "expert" in by_skill.index and "novice" in by_skill.index:
        assert by_skill["expert"] >= by_skill["novice"] - 0.05


def test_inefficient_operator_has_below_average_fuel_efficiency(tables):
    twin_df = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"])
    fleet_mean = twin_df["fuel_efficiency"].mean()
    inefficient_row = twin_df[twin_df["operator_id"] == config.INEFFICIENT_OPERATOR_ID].iloc[0]
    assert inefficient_row["fuel_efficiency"] < fleet_mean


def test_rain_sensitivity_direction_matches_generator_parameter(tables):
    """The twin doesn't see the generator's hidden `rain_sensitivity` input
    parameter directly (only the real operators.csv field, which IS
    legitimate input data) — but operators with a higher generator
    rain_sensitivity parameter should, on average, show up as more
    rain-sensitive in the twin's data-driven estimate too."""
    twin_df = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"])
    merged = twin_df.merge(
        tables["operators"][["operator_id", "rain_sensitivity"]], on="operator_id", suffixes=("_twin", "_true")
    )
    correlation = merged["rain_sensitivity_twin"].corr(merged["rain_sensitivity_true"])
    # A weak-to-moderate positive correlation is the honest bar here — the
    # synthetic signal is noisy by design, this just checks the sign is right.
    assert correlation > 0.0


def test_twin_as_of_cutoff_excludes_future_tasks(tables):
    """The core no-leakage guarantee: build_operator_twin(as_of=X) must never
    be influenced by a task that starts at or after X."""
    tasks = tables["tasks"].sort_values("start_time")
    cutoff = tasks.iloc[len(tasks) // 2]["start_time"]

    twin_df = build_operator_twin(tables["tasks"], tables["telemetry"], tables["operators"], as_of=cutoff)
    expected_counts = (
        tasks[tasks["start_time"] < cutoff].groupby("operator_id").size()
    )
    for _, row in twin_df.iterrows():
        assert row["n_tasks"] == expected_counts.get(row["operator_id"], 0)
