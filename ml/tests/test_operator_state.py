"""Tests for the unified operator intelligence entry point,
`generate_operator_state()`."""

import pandas as pd
import pytest

from src.common import config
from src.intelligence.operator_state import generate_operator_state

REQUIRED_KEYS = {
    "operator_twin",
    "eta",
    "dynamic_eta",
    "remaining_work",
    "risk",
    "habits",
    "idle_analysis",
    "focus",
    "fuel_diagnosis",
    "training",
    "threat_briefing",
    "explanations",
}


def test_complete_output_structure(eta_bundle):
    # Ensure the module-level eta model cache is warm without a real disk
    # write — see conftest for eta_bundle. generate_operator_state() loads
    # its own model via load_eta_model(), so this also exercises that path
    # once run_eta_pipeline.py has been run at least once locally.
    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)
    assert REQUIRED_KEYS <= set(state.keys())
    assert state["operator_id"] == config.DEMO_OPERATOR_ID
    assert state["machine_id"] == config.DEMO_MACHINE_ID
    assert state["task_id"] == config.DEMO_TASK_ID


def test_demo_operator_matches_underlying_modules():
    """Cross-check: the unified state's numbers must match what calling the
    underlying modules directly would produce — no silent divergence from
    orchestration."""
    from src.operator_twin.twin import get_operator_profile
    from src.common.loaders import load_operators, load_tasks, load_telemetry

    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)

    direct_twin = get_operator_profile(
        config.DEMO_OPERATOR_ID, load_tasks(), load_telemetry(), load_operators()
    )
    assert state["operator_twin"] == direct_twin


def test_unknown_task_id_raises_clear_error():
    with pytest.raises(ValueError):
        generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, "NOT_A_REAL_TASK")


def test_pre_task_state_has_full_remaining_work():
    """With no telemetry_so_far provided, the state should represent a task
    that hasn't started yet — full buckets remaining, not partial."""
    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)
    assert state["remaining_work"]["buckets_completed"] == 0
    assert state["remaining_work"]["buckets_remaining"] == state["remaining_work"]["total_buckets"]
    assert state["eta"]["eta_point"] == state["dynamic_eta"]["eta_point"]


def test_missing_optional_context_uses_safe_defaults():
    """Calling with current_context=None (or omitted) must not error."""
    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID, None)
    assert state["risk"]["risk_level"] in ("low", "medium", "high", "critical")


def test_context_includes_cache_for_realtime_updates():
    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)
    assert "_context" in state
    for key in ("tables", "task_features", "eta_bundle", "telemetry_so_far", "task_row"):
        assert key in state["_context"]


def test_no_values_are_none_where_a_real_result_is_expected():
    state = generate_operator_state(config.DEMO_OPERATOR_ID, config.DEMO_MACHINE_ID, config.DEMO_TASK_ID)
    assert state["eta"]["eta_point"] is not None
    assert state["operator_twin"]["paceFactor"] is not None
    assert state["risk"]["risk_level"] is not None
