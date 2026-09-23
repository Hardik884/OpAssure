"""Deterministic safety rules (handover §12-13).

Pure functions with no database access, so the synthetic generator, the replay
engine and the API all apply exactly the same rules.
"""

from dataclasses import dataclass

AVOIDABLE_IDLE_THRESHOLD_MIN = 5.0
LONG_IDLE_THRESHOLD_MIN = 8.0

PROXIMITY_CRITICAL_M = 15.0
PROXIMITY_CAUTION_M = 30.0
PROXIMITY_SAFE_M = 50.0


@dataclass(frozen=True)
class SafetyAlert:
    type: str
    severity: str  # warning | critical
    message: str


def evaluate_telemetry(
    *,
    seatbelt_status: str,
    machine_moving: bool,
    idling_time_min: float,
    idle_reason: str | None,
    engine_running: bool = True,
) -> SafetyAlert | None:
    """Return the most severe alert for one telemetry sample, or None."""
    unfastened = seatbelt_status == "unfastened"
    if machine_moving and unfastened:
        return SafetyAlert(
            "seatbelt_unfastened_while_moving", "critical", "Machine moving with seatbelt unfastened"
        )
    if unfastened and engine_running and not machine_moving and idling_time_min >= LONG_IDLE_THRESHOLD_MIN:
        return SafetyAlert(
            "possible_unattended_machine", "warning", "Engine running, seatbelt off, long idle"
        )
    if idle_reason == "avoidable" and idling_time_min > AVOIDABLE_IDLE_THRESHOLD_MIN:
        return SafetyAlert("avoidable_idle", "warning", "Avoidable idle above threshold")
    return None


def proximity_severity(distance_m: float) -> str:
    """50 m+ safe, <=30 m caution, <=15 m critical."""
    if distance_m <= PROXIMITY_CRITICAL_M:
        return "critical"
    if distance_m <= PROXIMITY_CAUTION_M:
        return "caution"
    return "safe"


def relative_direction(bearing_deg: float, heading_deg: float = 0.0) -> str:
    """Direction of a point relative to a machine facing `heading_deg` (0 = north)."""
    rel = (bearing_deg - heading_deg) % 360
    if rel < 45 or rel >= 315:
        return "front"
    if rel < 135:
        return "right"
    if rel < 225:
        return "rear"
    return "left"
