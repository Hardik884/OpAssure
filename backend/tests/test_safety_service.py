from app.services.safety_service import (
    distance_and_bearing, evaluate_all, evaluate_proximity, evaluate_telemetry, overall_status,
    proximity_severity, relative_direction,
)


def _eval(**overrides):
    row = {"seatbelt_status": "fastened", "machine_moving": True, "idling_time_min": 0.0, "idle_reason": None}
    return evaluate_telemetry(**(row | overrides))


def _all(**overrides):
    state = {"seatbelt_status": "fastened", "machine_moving": True, "idle_minutes": 0.0, "idle_reason": None}
    return evaluate_all(**(state | overrides))


def test_rule1_moving_unbelted_is_critical_seatbelt():
    alert = _eval(seatbelt_status="unfastened")
    assert (alert.type, alert.severity) == ("seatbelt", "critical")


def test_normal_operation_has_no_alert():
    assert _eval() is None
    assert _all() == []
    assert overall_status([]) == "safe"


def test_rule2_proximity_critical_only_when_moving():
    assert [(a.type, a.severity) for a in _all(worker_distance_m=12)] == [("proximity", "critical")]
    assert [(a.type, a.severity) for a in _all(machine_moving=False, worker_distance_m=12)] == [("proximity", "warning")]
    assert [(a.type, a.severity) for a in _all(worker_distance_m=25)] == [("proximity", "warning")]
    assert _all(worker_distance_m=40) == []
    assert _all(worker_distance_m=60) == []
    assert evaluate_proximity(12, True, "right").message == "Worker 12 m from machine (right side)"


def test_rule3_avoidable_idle_warns_but_truck_wait_does_not():
    alert = _eval(machine_moving=False, idling_time_min=9, idle_reason="avoidable")
    assert (alert.type, alert.severity) == ("avoidable_idle", "warning")
    assert _eval(machine_moving=False, idling_time_min=9, idle_reason="truck_wait") is None
    assert _eval(machine_moving=False, idling_time_min=5, idle_reason="avoidable") is None  # threshold is ">"


def test_rule4_unattended_machine():
    alert = _eval(seatbelt_status="unfastened", machine_moving=False, idling_time_min=10, idle_reason="truck_wait")
    assert (alert.type, alert.severity) == ("unattended_machine", "warning")
    assert _eval(seatbelt_status="unfastened", machine_moving=False, idling_time_min=3, idle_reason="truck_wait") is None
    assert _all(seatbelt_status="unfastened", machine_moving=False, idle_minutes=10, engine_running=False) == []


def test_alerts_sorted_most_severe_first():
    alerts = _all(seatbelt_status="unfastened", worker_distance_m=20)
    assert [a.type for a in alerts] == ["seatbelt", "proximity"]
    assert overall_status(alerts) == "critical"


def test_proximity_bands():
    assert proximity_severity(12) == "critical"
    assert proximity_severity(15) == "critical"
    assert proximity_severity(25) == "caution"
    assert proximity_severity(50) == "safe"


def test_relative_direction_and_distance():
    assert relative_direction(90) == "right"
    assert relative_direction(270) == "left"
    assert relative_direction(0) == "front"
    assert relative_direction(180) == "rear"
    dist, bearing = distance_and_bearing(40.0, -89.0, 40.0, -89.0 + 12 / (111_320 * 0.766))
    assert abs(dist - 12) < 0.2 and abs(bearing - 90) < 1
