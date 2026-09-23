"""Structured, deterministic explanations for an ETA prediction.

Every factor here is read off a measurable input (weather, the operator
twin, machine age, an observed cycle-time change) — nothing is phrased by an
LLM and nothing is invented. This is the "why" that pairs with the "what" in
`src.eta.inference` and `src.eta.dynamic`.
"""

from src.common import config


def _impact(value: float, threshold: float) -> str:
    if value > threshold:
        return "positive"
    if value < -threshold:
        return "negative"
    return "neutral"


def build_eta_explanation(
    task_row: dict,
    operator_twin: dict,
    weather_row: dict | None = None,
    cycle_time_change_pct: float | None = None,
) -> dict:
    """Return `{"reason": str, "factors": [{"name", "impact", "detail"}]}`.

    `cycle_time_change_pct` (e.g. 0.15 for +15%) is only present for dynamic
    (in-progress) ETA updates; static/pre-task explanations omit it.
    """
    factors = []
    headline_parts = []

    condition = (weather_row or {}).get("condition") or task_row.get("weather")
    if condition in ("rain", "storm"):
        factors.append({"name": "weather", "impact": "negative", "detail": f"{condition} conditions"})
        headline_parts.append(f"{condition} conditions are slowing progress")
    elif condition == "cloudy":
        factors.append({"name": "weather", "impact": "neutral", "detail": "cloudy conditions"})
    else:
        factors.append({"name": "weather", "impact": "positive", "detail": "clear conditions"})

    pace = operator_twin.get("paceFactor", 1.0)
    pace_impact = _impact(pace - 1.0, 0.03)
    factors.append(
        {
            "name": "operator_pace",
            "impact": pace_impact,
            "detail": f"{'faster' if pace_impact == 'positive' else 'slower' if pace_impact == 'negative' else 'typical'} than fleet average",
        }
    )
    if pace_impact == "positive":
        headline_parts.append("this operator typically runs faster than average")
    elif pace_impact == "negative":
        headline_parts.append("this operator typically runs slower than average")

    machine_age = task_row.get("machine_age")
    if machine_age is not None:
        age_impact = "negative" if machine_age >= 8 else "neutral"
        factors.append({"name": "machine_age", "impact": age_impact, "detail": f"{machine_age} years old"})
        if age_impact == "negative":
            headline_parts.append("an older machine")

    if cycle_time_change_pct is not None:
        impact = "negative" if cycle_time_change_pct > 0.05 else ("positive" if cycle_time_change_pct < -0.05 else "neutral")
        factors.append(
            {
                "name": "cycle_time_change",
                "impact": impact,
                "detail": f"{cycle_time_change_pct:+.0%} vs. planned cycle time",
            }
        )
        if impact == "negative":
            headline_parts.append(f"recent cycle time is running {cycle_time_change_pct:+.0%} vs. plan")
        elif impact == "positive":
            headline_parts.append(f"recent cycle time is {cycle_time_change_pct:+.0%} ahead of plan")

    afternoon_effect = operator_twin.get("afternoonEffect", 0.0)
    hour = task_row.get("hour_of_day")
    if hour is not None and hour >= config.DEFAULT_AFTERNOON_HOUR and afternoon_effect < -0.03:
        factors.append({"name": "afternoon_fatigue", "impact": "negative", "detail": "afternoon start time"})
        headline_parts.append("an afternoon start (this operator tends to slow down later in the day)")

    if headline_parts:
        reason = "; ".join(headline_parts).capitalize() + "."
    else:
        reason = "No significant deviation from typical conditions."

    return {"reason": reason, "factors": factors}
