"""Tests for the Pre-Task Threat Briefing: risk source correctness, ranking,
the top-3 limit, and the honest empty case."""

from src.common import config
from src.safety.threat_briefing import generate_threat_briefing

NEUTRAL_TWIN = {"paceFactor": 1.0, "afternoonEffect": 0.0, "rainSensitivity": 0.0, "heatSensitivity": 0.0}


def _task(**overrides):
    row = {"weather": "clear", "temperature": 20.0, "hour_of_day": 9.0}
    row.update(overrides)
    return row


def test_weather_driven_risk():
    result = generate_threat_briefing(_task(weather="rain"), NEUTRAL_TWIN)
    assert any(r["source"] == "weather" for r in result)


def test_operator_driven_risk_from_habit():
    habit = {"is_habit": True, "count": 5, "opportunities": 12, "frequency": 0.42}
    result = generate_threat_briefing(_task(), NEUTRAL_TWIN, habit_summary=habit)
    assert result[0]["source"] == "safety"  # highest severity, ranked first


def test_operator_driven_risk_from_afternoon_effect():
    twin = {**NEUTRAL_TWIN, "afternoonEffect": -0.2}
    result = generate_threat_briefing(_task(hour_of_day=15.0), twin)
    assert any(r["source"] == "operator" for r in result)


def test_machine_driven_risk():
    result = generate_threat_briefing(_task(), NEUTRAL_TWIN, machine_degrading=True)
    assert any(r["source"] == "machine" for r in result)


def test_site_driven_risk_from_proximity_events():
    result = generate_threat_briefing(_task(), NEUTRAL_TWIN, site_near_miss_count=config.TRAINING_MIN_PROXIMITY_EVENTS)
    assert any(r["source"] == "site" for r in result)


def test_multiple_risks_ranked_by_severity():
    habit = {"is_habit": True, "count": 5, "opportunities": 12, "frequency": 0.42}
    result = generate_threat_briefing(
        _task(weather="storm"),
        NEUTRAL_TWIN,
        habit_summary=habit,
        machine_degrading=True,
        site_near_miss_count=5,
    )
    severities_should_be_descending = [r["priority"] for r in result]
    assert severities_should_be_descending == sorted(severities_should_be_descending)
    assert result[0]["source"] == "safety"  # the habit is the most severe here


def test_top_3_limit_enforced():
    habit = {"is_habit": True, "count": 5, "opportunities": 12, "frequency": 0.42}
    twin = {**NEUTRAL_TWIN, "afternoonEffect": -0.2, "rainSensitivity": 0.3, "heatSensitivity": 0.3}
    result = generate_threat_briefing(
        _task(weather="storm", temperature=40.0, hour_of_day=15.0),
        twin,
        habit_summary=habit,
        machine_degrading=True,
        recent_safety_alert_count=3,
        site_near_miss_count=5,
    )
    assert len(result) <= config.THREAT_BRIEFING_TOP_N


def test_empty_briefing_when_nothing_notable():
    result = generate_threat_briefing(_task(), NEUTRAL_TWIN)
    assert result == []


def test_priorities_are_sequential_starting_at_one():
    habit = {"is_habit": True, "count": 5, "opportunities": 12, "frequency": 0.42}
    result = generate_threat_briefing(_task(weather="rain"), NEUTRAL_TWIN, habit_summary=habit, machine_degrading=True)
    assert [r["priority"] for r in result] == list(range(1, len(result) + 1))
