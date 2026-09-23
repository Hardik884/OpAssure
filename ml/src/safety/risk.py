"""Safety / risk intelligence: a contextual layer ON TOP OF a deterministic
safety engine — it never gets to soften a hard safety condition.

Two hard rules are checked FIRST and unconditionally override everything
else (per the project rule: "Do not allow an ML score to downgrade an
obvious critical safety condition"):

  1. machine moving + seatbelt unfastened -> always "critical"
  2. a worker inside the swing-zone radius while the machine is moving ->
     always "critical"

Only when neither hard rule fires does this module compute a contextual
0-100 score from softer signals (recent safety alerts, a detected habit,
weather, machine degradation, "somewhat close" proximity) to produce
medium/high/low risk.
"""

from src.common import config

HARD_RULE_SEATBELT = "seatbelt_unfastened_while_moving"
HARD_RULE_PROXIMITY = "worker_in_swing_zone_while_moving"


def _risk_level_from_score(score: float) -> str:
    for level, threshold in config.RISK_LEVEL_BANDS:
        if score >= threshold:
            return level
    return "low"


def calculate_risk(
    seatbelt_status: str,
    machine_moving: bool,
    nearest_worker_distance_m: float | None = None,
    recent_safety_alert_count: int = 0,
    weather_condition: str = "clear",
    persistent_habit: bool = False,
    machine_degrading: bool = False,
) -> dict:
    """Compute the contextual risk result for one machine/operator moment.

    Hard-rule critical conditions set `score = 100` and `hard_rule_triggered`
    to the rule's name — that flag is what proves (and lets a test verify)
    the score didn't quietly downgrade an unsafe condition.
    """
    # --- Hard rule 1: unfastened seatbelt while moving ---------------------
    if machine_moving and seatbelt_status == "unbuckled":
        return {
            "risk_level": "critical",
            "score": 100,
            "factors": ["seatbelt_unfastened_while_moving"],
            "explanation": "Machine is moving with the seatbelt unfastened — critical, non-negotiable.",
            "hard_rule_triggered": HARD_RULE_SEATBELT,
        }

    # --- Hard rule 2: worker inside the swing zone while moving -------------
    if (
        machine_moving
        and nearest_worker_distance_m is not None
        and nearest_worker_distance_m <= config.SWING_ZONE_RADIUS_M
    ):
        return {
            "risk_level": "critical",
            "score": 100,
            "factors": ["worker_in_swing_zone_while_moving"],
            "explanation": (
                f"A worker is {nearest_worker_distance_m:.1f}m from a moving machine — "
                f"inside the {config.SWING_ZONE_RADIUS_M:.0f}m swing zone. Critical."
            ),
            "hard_rule_triggered": HARD_RULE_PROXIMITY,
        }

    # --- Contextual scoring (no hard rule triggered) ------------------------
    score = 10.0
    factors = []

    if recent_safety_alert_count > 0:
        score += min(30.0, recent_safety_alert_count * 8)
        factors.append(f"{recent_safety_alert_count} recent safety alert(s)")

    if persistent_habit:
        score += 15.0
        factors.append("persistent unsafe habit detected (Habit Radar)")

    if weather_condition in ("rain", "storm"):
        score += 10.0
        factors.append(f"{weather_condition} conditions")

    if machine_degrading:
        score += 10.0
        factors.append("machine showing a degradation trend")

    if (
        nearest_worker_distance_m is not None
        and machine_moving
        and nearest_worker_distance_m <= config.SWING_ZONE_RADIUS_M * config.RISK_PROXIMITY_ELEVATED_MULTIPLIER
    ):
        score += 15.0
        factors.append(f"worker {nearest_worker_distance_m:.1f}m away (elevated, not yet in swing zone)")

    score = round(min(100.0, score))
    risk_level = _risk_level_from_score(score)

    if not factors:
        explanation = "No elevated risk factors observed."
    else:
        explanation = "Elevated risk from: " + "; ".join(factors) + "."

    return {
        "risk_level": risk_level,
        "score": score,
        "factors": factors,
        "explanation": explanation,
        "hard_rule_triggered": None,
    }


def get_risk_factors(*args, **kwargs) -> list[str]:
    """Thin convenience wrapper: just the factor list from `calculate_risk()`."""
    return calculate_risk(*args, **kwargs)["factors"]
