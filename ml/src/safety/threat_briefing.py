"""Pre-Task Threat Briefing: the top 3 structured, fact-grounded risks for
an upcoming task — no LLM decides the numbers, and nothing is invented when
there's genuinely nothing notable to report.

Every candidate risk below is tied to an actual computed value (a weather
reading, a Twin sensitivity, a feature-pipeline degradation signal, a real
count of near-misses/alerts) — this module only ranks and selects the top 3,
it doesn't compute any of them itself.
"""

import pandas as pd

from src.common import config


def _candidate_risks(
    task_row: dict,
    operator_twin: dict,
    habit_summary: dict | None,
    machine_degrading: bool,
    recent_safety_alert_count: int,
    site_near_miss_count: int,
) -> list[dict]:
    candidates = []

    # --- safety: a real, already-detected unsafe habit -----------------------
    if habit_summary and habit_summary.get("is_habit"):
        candidates.append(
            {
                "severity": 90,
                "risk": "Recurring seatbelt-during-truck-wait pattern for this operator.",
                "reason": (
                    f"Habit Radar: {habit_summary['count']}/{habit_summary['opportunities']} "
                    f"truck-wait opportunities ({habit_summary['frequency']:.0%})."
                ),
                "source": "safety",
            }
        )

    # --- safety: recent safety alerts on this machine/operator ----------------
    if recent_safety_alert_count > 0:
        candidates.append(
            {
                "severity": 70 + min(20, recent_safety_alert_count * 5),
                "risk": "Recent seatbelt/safety alerts recorded on this machine.",
                "reason": f"{recent_safety_alert_count} safety alert(s) in recent telemetry.",
                "source": "safety",
            }
        )

    # --- site: repeated proximity/near-miss events at this machine -----------
    if site_near_miss_count >= config.TRAINING_MIN_PROXIMITY_EVENTS:
        candidates.append(
            {
                "severity": 65,
                "risk": "Workers have repeatedly entered this machine's swing zone recently.",
                "reason": f"{site_near_miss_count} near-miss event(s) recorded at this machine.",
                "source": "site",
            }
        )

    # --- machine: a real degradation trend from the feature pipeline ---------
    if machine_degrading:
        candidates.append(
            {
                "severity": 55,
                "risk": "This machine is trending toward longer cycle times.",
                "reason": "Recent tasks on this machine are running slower than its own historical average.",
                "source": "machine",
            }
        )

    # --- weather: wet or hot conditions, weighted by the operator's own Twin --
    condition = task_row.get("weather")
    temperature = task_row.get("temperature")
    if condition in ("rain", "storm"):
        rain_sensitivity = operator_twin.get("rainSensitivity", 0.0)
        severity = 40 + min(30, rain_sensitivity * 100)
        candidates.append(
            {
                "severity": severity,
                "risk": f"{condition.capitalize()} conditions expected for this task.",
                "reason": (
                    f"Forecast/recorded condition: {condition}"
                    + (f"; this operator's rain sensitivity is {rain_sensitivity:.0%}." if rain_sensitivity else ".")
                ),
                "source": "weather",
            }
        )
    if temperature is not None and temperature > config.HEAT_TEMP_THRESHOLD_C:
        heat_sensitivity = operator_twin.get("heatSensitivity", 0.0)
        severity = 35 + min(30, heat_sensitivity * 100)
        candidates.append(
            {
                "severity": severity,
                "risk": "High temperature expected during this task.",
                "reason": (
                    f"Temperature {temperature:.0f}°C"
                    + (f"; this operator's heat sensitivity is {heat_sensitivity:.0%}." if heat_sensitivity else ".")
                ),
                "source": "weather",
            }
        )

    # --- operator: historical afternoon slowdown, if the task starts late ----
    hour_of_day = task_row.get("hour_of_day")
    afternoon_effect = operator_twin.get("afternoonEffect", 0.0)
    if (
        hour_of_day is not None
        and hour_of_day >= config.DEFAULT_AFTERNOON_HOUR
        and afternoon_effect <= config.TRAINING_AFTERNOON_EFFECT_THRESHOLD
    ):
        candidates.append(
            {
                "severity": 30,
                "risk": "This operator has a measurable afternoon slowdown pattern.",
                "reason": f"Operator Twin afternoonEffect = {afternoon_effect:.0%}, and this task starts in the afternoon.",
                "source": "operator",
            }
        )

    return candidates


def generate_threat_briefing(
    task_row: dict,
    operator_twin: dict,
    habit_summary: dict | None = None,
    machine_degrading: bool = False,
    recent_safety_alert_count: int = 0,
    site_near_miss_count: int = 0,
    top_n: int = config.THREAT_BRIEFING_TOP_N,
) -> list[dict]:
    """Return the top `top_n` risks for this task, ranked by severity.

    Returns an empty list when nothing qualifies — an empty briefing IS the
    honest "no meaningful risk identified" answer; callers/UI should treat
    an empty list as exactly that, not as a missing/failed computation.
    """
    candidates = _candidate_risks(
        task_row, operator_twin, habit_summary, machine_degrading, recent_safety_alert_count, site_near_miss_count
    )
    ranked = sorted(candidates, key=lambda c: c["severity"], reverse=True)[:top_n]

    return [
        {"priority": i + 1, "risk": c["risk"], "reason": c["reason"], "source": c["source"]}
        for i, c in enumerate(ranked)
    ]
