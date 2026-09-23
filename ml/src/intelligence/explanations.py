"""Structured explanations for every subsystem, in one consistent shape:
`{"reason": str, "factors": [{"name", "impact", "detail"}]}`.

Every function here is a thin adapter over a module's OWN already-computed
result — none of them recompute anything or invent a number. Most modules
already produce a `reason`/`explanation` field for exactly this purpose;
these adapters just normalize the key names and, where useful, derive a
`factors` list from fields that were already part of the result.

No LLM is used for any of this. If an LLM-based narration layer is ever
added on top, it should consume these structured results as its input and
this module remains the deterministic fallback — these functions never
depend on an LLM being available.
"""


def explain_eta(eta_result: dict) -> dict:
    return {"reason": eta_result.get("reason", ""), "factors": eta_result.get("factors", [])}


def explain_operator_twin(twin: dict) -> dict:
    factors = []
    pace = twin.get("paceFactor", 1.0)
    factors.append({"name": "pace", "impact": "positive" if pace > 1.03 else "negative" if pace < 0.97 else "neutral", "detail": f"paceFactor={pace}"})
    if twin.get("rainSensitivity", 0) >= 0.1:
        factors.append({"name": "rain_sensitivity", "impact": "negative", "detail": f"{twin['rainSensitivity']:.0%}"})
    if twin.get("heatSensitivity", 0) >= 0.1:
        factors.append({"name": "heat_sensitivity", "impact": "negative", "detail": f"{twin['heatSensitivity']:.0%}"})
    if twin.get("afternoonEffect", 0) <= -0.05:
        factors.append({"name": "afternoon_effect", "impact": "negative", "detail": f"{twin['afternoonEffect']:.0%}"})
    fuel = twin.get("fuelEfficiency", 1.0)
    if fuel < 0.95 or fuel > 1.05:
        factors.append({"name": "fuel_efficiency", "impact": "positive" if fuel > 1.0 else "negative", "detail": f"{fuel}"})

    reason = (
        f"Operator {twin.get('operatorId', '')} is {'faster' if pace > 1.0 else 'slower' if pace < 1.0 else 'typical'} "
        f"than the fleet average, based on {twin.get('nTasks', 0)} observed tasks."
    )
    return {"reason": reason, "factors": factors}


def explain_habit(habit_summary: dict) -> dict:
    return {
        "reason": habit_summary.get("explanation", ""),
        "factors": [
            {
                "name": habit_summary.get("habit_type", "habit"),
                "impact": "negative" if habit_summary.get("is_habit") else "neutral",
                "detail": f"{habit_summary.get('count', 0)}/{habit_summary.get('opportunities', 0)} "
                f"({habit_summary.get('frequency', 0.0):.0%})",
            }
        ],
    }


def explain_idle(idle_result: dict) -> dict:
    if "dominant_idle_type" in idle_result:  # classify_task_idle() shape
        return {
            "reason": f"Idle time was predominantly {idle_result['dominant_idle_type']} for this task.",
            "factors": [
                {"name": "legitimate_idle_min", "impact": "neutral", "detail": idle_result["legitimate_idle_min"]},
                {"name": "avoidable_idle_min", "impact": "negative" if idle_result["avoidable_idle_min"] > 0 else "neutral", "detail": idle_result["avoidable_idle_min"]},
            ],
        }
    # classify_idle() row-level shape
    return {
        "reason": idle_result.get("reason", ""),
        "factors": [{"name": "idle_type", "impact": "neutral" if idle_result.get("idle_type") == "legitimate" else "negative", "detail": idle_result.get("confidence")}],
    }


def explain_focus(focus_result: dict) -> dict:
    factors = [{"name": "focus_factor", "impact": "negative", "detail": f} for f in focus_result.get("factors", [])]
    score = focus_result.get("score", 100)
    reason = (
        f"Focus score {score}/100"
        + (f" — driven by: {', '.join(focus_result['factors'])}." if focus_result.get("factors") else " — no significant factors.")
    )
    return {"reason": reason, "factors": factors}


def explain_risk(risk_result: dict) -> dict:
    return {
        "reason": risk_result.get("explanation", ""),
        "factors": [{"name": f, "impact": "negative", "detail": None} for f in risk_result.get("factors", [])],
    }


def explain_diagnosis(findings: list[dict]) -> dict:
    if not findings:
        return {"reason": "No elevated fuel-use pattern found for this operator/machine.", "factors": []}
    factors = [{"name": f["source"], "impact": "negative", "detail": f["evidence"]} for f in findings]
    reason = "; ".join(f["evidence"] for f in findings)
    return {"reason": reason, "factors": factors}


def explain_training(training_result: dict) -> dict:
    if not training_result.get("recommended"):
        return {"reason": training_result.get("reason", "No training recommended."), "factors": []}
    return {
        "reason": training_result.get("reason", ""),
        "factors": [{"name": "trigger_type", "impact": "negative", "detail": training_result.get("trigger_type")}],
    }


def explain_threat_briefing(briefing: list[dict]) -> dict:
    if not briefing:
        return {"reason": "No significant risks identified for this task.", "factors": []}
    factors = [{"name": r["source"], "impact": "negative", "detail": r["risk"]} for r in briefing]
    reason = "; ".join(r["risk"] for r in briefing)
    return {"reason": reason, "factors": factors}
