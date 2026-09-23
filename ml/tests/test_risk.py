"""Tests for the risk/safety intelligence layer — especially the guarantee
that hard critical conditions can never be downgraded by contextual scoring."""

from src.common import config
from src.evaluation.behaviour_eval import evaluate_seatbelt_critical_detection
from src.safety.risk import calculate_risk, get_risk_factors


def test_safe_condition_is_low_risk():
    result = calculate_risk(seatbelt_status="buckled", machine_moving=True)
    assert result["risk_level"] == "low"
    assert result["hard_rule_triggered"] is None


def test_medium_risk_from_contextual_factors():
    result = calculate_risk(
        seatbelt_status="buckled",
        machine_moving=True,
        recent_safety_alert_count=2,
        weather_condition="rain",
    )
    assert result["risk_level"] in ("medium", "high")
    assert result["hard_rule_triggered"] is None
    assert len(result["factors"]) > 0


def test_critical_seatbelt_condition():
    result = calculate_risk(seatbelt_status="unbuckled", machine_moving=True)
    assert result["risk_level"] == "critical"
    assert result["score"] == 100
    assert result["hard_rule_triggered"] == "seatbelt_unfastened_while_moving"


def test_seatbelt_unbuckled_while_stationary_is_not_critical():
    """The hard rule is specifically moving + unbuckled — unbuckled while
    stopped is not itself a critical condition."""
    result = calculate_risk(seatbelt_status="unbuckled", machine_moving=False)
    assert result["risk_level"] != "critical"


def test_critical_proximity_condition():
    result = calculate_risk(
        seatbelt_status="buckled",
        machine_moving=True,
        nearest_worker_distance_m=config.SWING_ZONE_RADIUS_M - 1,
    )
    assert result["risk_level"] == "critical"
    assert result["hard_rule_triggered"] == "worker_in_swing_zone_while_moving"


def test_proximity_outside_swing_zone_is_not_automatically_critical():
    result = calculate_risk(
        seatbelt_status="buckled",
        machine_moving=True,
        nearest_worker_distance_m=config.SWING_ZONE_RADIUS_M * 5,
    )
    assert result["risk_level"] != "critical"


def test_critical_conditions_cannot_be_downgraded_by_context():
    """Even when every contextual factor points toward 'looks fine' (no
    alerts, clear weather, no habit, no degradation), the hard rule must
    still win and produce score=100/critical."""
    result = calculate_risk(
        seatbelt_status="unbuckled",
        machine_moving=True,
        recent_safety_alert_count=0,
        weather_condition="clear",
        persistent_habit=False,
        machine_degrading=False,
    )
    assert result["risk_level"] == "critical"
    assert result["score"] == 100


def test_both_hard_rules_triggered_simultaneously_still_critical():
    result = calculate_risk(
        seatbelt_status="unbuckled",
        machine_moving=True,
        nearest_worker_distance_m=1.0,
    )
    assert result["risk_level"] == "critical"
    assert result["score"] == 100


def test_get_risk_factors_matches_calculate_risk():
    factors = get_risk_factors(seatbelt_status="unbuckled", machine_moving=True)
    assert factors == calculate_risk(seatbelt_status="unbuckled", machine_moving=True)["factors"]


def test_seatbelt_critical_detection_matches_real_telemetry(tables):
    """The hard rule should essentially perfectly reproduce the dataset's
    own safety_alert column (moving + unbuckled), since that's exactly how
    safety_alert was defined at generation time."""
    report = evaluate_seatbelt_critical_detection(tables["telemetry"])
    assert report["precision"] > 0.99
    assert report["recall"] > 0.99
