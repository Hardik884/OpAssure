"""Tests for Focus Battery: bounded score, factor triggers, and the
explicit non-medical disclaimer."""

import pandas as pd

from src.safety.focus_battery import calculate_focus, get_focus_recommendation

NEUTRAL_TWIN = {"paceFactor": 1.0, "afternoonEffect": 0.0, "heatSensitivity": 0.1}


def _tasks(rows):
    return pd.DataFrame(rows)


def _weather(temperature: float, at: pd.Timestamp):
    return pd.DataFrame([{"timestamp": at - pd.Timedelta(hours=1), "temperature": temperature}])


def test_normal_morning_condition_scores_high():
    as_of = pd.Timestamp("2026-06-01 08:00:00")
    tasks = _tasks(
        [{"operator_id": "OPX", "start_time": as_of - pd.Timedelta(minutes=30), "actual_time_min": 30}]
    )
    weather = _weather(18.0, as_of)
    result = calculate_focus("OPX", as_of, tasks, weather, NEUTRAL_TWIN)
    assert result["score"] >= 85
    assert 0 <= result["score"] <= 100


def test_prolonged_continuous_work_lowers_score():
    as_of = pd.Timestamp("2026-06-01 13:00:00")
    start = pd.Timestamp("2026-06-01 07:00:00")
    tasks = _tasks([{"operator_id": "OPX", "start_time": start, "actual_time_min": 6 * 60}])  # 6h continuous
    weather = _weather(18.0, as_of)
    result = calculate_focus("OPX", as_of, tasks, weather, NEUTRAL_TWIN)
    assert result["score"] < 100
    assert any("continuous work" in f for f in result["factors"])


def test_heat_effect_lowers_score():
    as_of = pd.Timestamp("2026-06-01 10:00:00")
    tasks = _tasks([{"operator_id": "OPX", "start_time": as_of - pd.Timedelta(minutes=20), "actual_time_min": 20}])
    hot_weather = _weather(38.0, as_of)
    cool_weather = _weather(18.0, as_of)

    hot_result = calculate_focus("OPX", as_of, tasks, hot_weather, NEUTRAL_TWIN)
    cool_result = calculate_focus("OPX", as_of, tasks, cool_weather, NEUTRAL_TWIN)

    assert hot_result["score"] < cool_result["score"]
    assert any("temperature" in f for f in hot_result["factors"])


def test_afternoon_effect_lowers_score_when_twin_shows_slowdown():
    as_of = pd.Timestamp("2026-06-01 15:00:00")
    tasks = _tasks([{"operator_id": "OPX", "start_time": as_of - pd.Timedelta(minutes=10), "actual_time_min": 10}])
    weather = _weather(18.0, as_of)

    slow_afternoon_twin = {"paceFactor": 1.0, "afternoonEffect": -0.15, "heatSensitivity": 0.1}
    neutral_result = calculate_focus("OPX", as_of, tasks, weather, NEUTRAL_TWIN)
    slow_result = calculate_focus("OPX", as_of, tasks, weather, slow_afternoon_twin)

    assert slow_result["score"] < neutral_result["score"]
    assert any("afternoon" in f for f in slow_result["factors"])


def test_score_always_bounded_0_to_100():
    as_of = pd.Timestamp("2026-06-01 16:00:00")
    start = pd.Timestamp("2026-06-01 07:00:00")
    # Deliberately extreme inputs to try to push the score out of bounds.
    tasks = _tasks(
        [{"operator_id": "OPX", "start_time": start, "actual_time_min": 9 * 60}]
        + [
            {
                "operator_id": "OPX",
                "start_time": start + pd.Timedelta(minutes=i * 20),
                "actual_time_min": 15,
            }
            for i in range(20)
        ]
    )
    extreme_weather = _weather(48.0, as_of)
    extreme_twin = {"paceFactor": 0.5, "afternoonEffect": -0.9, "heatSensitivity": 1.0}
    result = calculate_focus("OPX", as_of, tasks, extreme_weather, extreme_twin, recent_cycle_time_ratio=3.0)
    assert 0 <= result["score"] <= 100


def test_disclaimer_is_present_and_not_medical():
    as_of = pd.Timestamp("2026-06-01 08:00:00")
    tasks = _tasks([{"operator_id": "OPX", "start_time": as_of, "actual_time_min": 10}])
    weather = _weather(18.0, as_of)
    result = calculate_focus("OPX", as_of, tasks, weather, NEUTRAL_TWIN)
    assert "not a medical" in result["disclaimer"].lower()


def test_recommendation_matches_score_band():
    low_result = get_focus_recommendation({"operator_id": "OPX", "score": 40, "factors": [], "disclaimer": "x"})
    mid_result = get_focus_recommendation({"operator_id": "OPX", "score": 60, "factors": [], "disclaimer": "x"})
    high_result = get_focus_recommendation({"operator_id": "OPX", "score": 90, "factors": [], "disclaimer": "x"})

    assert "break" in low_result["recommendation"].lower()
    assert "break" in mid_result["recommendation"].lower()
    assert "no action needed" in high_result["recommendation"].lower()
