"""Deterministic safety rules (handover §12-13). No ML involved.

Pure functions with no database access, so the synthetic generator, the REST API
and the replay engine all apply exactly the same rules.

Rule 1  seatbelt            moving + seatbelt unfastened                   -> critical
Rule 2  proximity           moving + worker <= 15 m                        -> critical
                            worker <= 30 m (or <= 15 m while stationary)   -> warning
Rule 3  avoidable_idle      idle > 5 min with idle_reason "avoidable"      -> warning
Rule 4  unattended_machine  unfastened + engine on + not moving + idle >= 8 min -> warning
"""

import math
from dataclasses import asdict, dataclass

AVOIDABLE_IDLE_THRESHOLD_MIN = 5.0
LONG_IDLE_THRESHOLD_MIN = 8.0

PROXIMITY_CRITICAL_M = 15.0
PROXIMITY_CAUTION_M = 30.0
PROXIMITY_SAFE_M = 50.0

SEVERITY_RANK = {"safe": 0, "warning": 1, "critical": 2}


@dataclass(frozen=True)
class SafetyAlert:
    type: str  # seatbelt | proximity | avoidable_idle | unattended_machine
    severity: str  # warning | critical
    message: str

    def to_dict(self) -> dict:
        return asdict(self)


def proximity_severity(distance_m: float) -> str:
    """Handover bands: <=15 m critical, <=30 m caution, otherwise safe (50 m+ is clear)."""
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


def distance_and_bearing(lat1: float, lon1: float, lat2: float, lon2: float) -> tuple[float, float]:
    """Metres and bearing (deg, 0 = north) from point 1 to point 2. Flat-earth; fine on one site."""
    north = (lat2 - lat1) * 111_320.0
    east = (lon2 - lon1) * 111_320.0 * math.cos(math.radians((lat1 + lat2) / 2))
    return math.hypot(east, north), math.degrees(math.atan2(east, north)) % 360


def evaluate_proximity(distance_m: float, machine_moving: bool, direction: str | None = None) -> SafetyAlert | None:
    band = proximity_severity(distance_m)
    if band == "safe":
        return None
    severity = "critical" if band == "critical" and machine_moving else "warning"
    where = f" ({direction} side)" if direction else ""
    return SafetyAlert("proximity", severity, f"Worker {distance_m:.0f} m from machine{where}")


def evaluate_all(
    *,
    seatbelt_status: str,
    machine_moving: bool,
    idle_minutes: float,
    idle_reason: str | None,
    engine_running: bool = True,
    worker_distance_m: float | None = None,
    worker_direction: str | None = None,
) -> list[SafetyAlert]:
    """Every alert for one machine state, most severe first.

    `idle_minutes` is how long the machine has been idle (continuous), not just the
    last sample interval.
    """
    alerts: list[SafetyAlert] = []
    unfastened = seatbelt_status == "unfastened"
    if machine_moving and unfastened:
        alerts.append(SafetyAlert("seatbelt", "critical", "Machine moving with seatbelt unfastened"))
    if worker_distance_m is not None:
        prox = evaluate_proximity(worker_distance_m, machine_moving, worker_direction)
        if prox:
            alerts.append(prox)
    if unfastened and engine_running and not machine_moving and idle_minutes >= LONG_IDLE_THRESHOLD_MIN:
        alerts.append(SafetyAlert(
            "unattended_machine", "warning",
            f"Engine running, seatbelt off, idle {idle_minutes:.0f} min - machine may be unattended",
        ))
    if idle_reason == "avoidable" and idle_minutes > AVOIDABLE_IDLE_THRESHOLD_MIN:
        alerts.append(SafetyAlert("avoidable_idle", "warning", f"Avoidable idle for {idle_minutes:.0f} min"))
    alerts.sort(key=lambda a: -SEVERITY_RANK[a.severity])
    return alerts


def evaluate_telemetry(
    *,
    seatbelt_status: str,
    machine_moving: bool,
    idling_time_min: float,
    idle_reason: str | None,
    engine_running: bool = True,
) -> SafetyAlert | None:
    """Most severe alert for one telemetry sample (used to fill telemetry.safety_alert)."""
    alerts = evaluate_all(seatbelt_status=seatbelt_status, machine_moving=machine_moving,
                          idle_minutes=idling_time_min, idle_reason=idle_reason,
                          engine_running=engine_running)
    return alerts[0] if alerts else None


def overall_status(alerts: list[SafetyAlert]) -> str:
    """safe | warning | critical."""
    return max((a.severity for a in alerts), key=SEVERITY_RANK.__getitem__, default="safe")
