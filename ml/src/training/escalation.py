"""Instructor escalation: deterministic, and never triggered from a single
observation or from incomplete evidence.

Escalation only fires when a FULL observation window (`config.TRAINING_OBSERVATION_WINDOW`)
of post-training data shows no meaningful improvement (`status` is
`"worsening"` or `"no_change"` from `evaluate_training_effect()`). Incomplete
evidence (`"insufficient_evidence"`) never escalates — that would be
punishing an operator before there's even enough data to judge them.
"""

from src.common import config


def check_escalation(effect_result: dict) -> dict:
    """Take an `evaluate_training_effect()` result and decide whether to
    escalate to an instructor session."""
    status = effect_result.get("status")

    if status == "insufficient_evidence":
        return {"escalate": False, "reason": "Not enough post-training observations yet to judge effect."}

    if status == "improving":
        return {"escalate": False}

    if status in ("worsening", "no_change"):
        metric = effect_result.get("metric_type", "the targeted behaviour")
        return {
            "escalate": True,
            "reason": (
                f"No meaningful improvement in {metric} after {effect_result.get('observations')} "
                f"post-training observations (status: {status})."
            ),
            "recommended_session_minutes": config.ESCALATION_SESSION_MINUTES,
        }

    # Unknown/absent status (e.g. no training record at all) — nothing to escalate.
    return {"escalate": False, "reason": "No training-effect result available to evaluate."}
