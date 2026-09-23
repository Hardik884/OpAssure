from app.services.safety_service import evaluate_telemetry, proximity_severity, relative_direction


def _eval(**overrides):
    row = {"seatbelt_status": "fastened", "machine_moving": True, "idling_time_min": 0.0, "idle_reason": None}
    return evaluate_telemetry(**(row | overrides))


def test_moving_unbelted_is_critical():
    alert = _eval(seatbelt_status="unfastened")
    assert alert.type == "seatbelt_unfastened_while_moving"
    assert alert.severity == "critical"


def test_normal_operation_has_no_alert():
    assert _eval() is None


def test_unbelted_long_idle_is_possible_unattended_warning():
    alert = _eval(seatbelt_status="unfastened", machine_moving=False, idling_time_min=10, idle_reason="truck_wait")
    assert (alert.type, alert.severity) == ("possible_unattended_machine", "warning")


def test_avoidable_idle_warns_but_truck_wait_does_not():
    alert = _eval(machine_moving=False, idling_time_min=9, idle_reason="avoidable")
    assert (alert.type, alert.severity) == ("avoidable_idle", "warning")
    assert _eval(machine_moving=False, idling_time_min=9, idle_reason="truck_wait") is None


def test_proximity_bands():
    assert proximity_severity(12) == "critical"
    assert proximity_severity(15) == "critical"
    assert proximity_severity(25) == "caution"
    assert proximity_severity(50) == "safe"


def test_relative_direction():
    assert relative_direction(90) == "right"
    assert relative_direction(270) == "left"
    assert relative_direction(0) == "front"
    assert relative_direction(180) == "rear"
