"""Clean inference interface for the ETA subsystem — what the backend calls.

Two entry points:
  - `predict_eta(task_features)`            -> a single point prediction (minutes)
  - `predict_personalized_eta(task_features, ...)` -> the full structured
    result: point estimate, [eta_min, eta_max] interval, the naive planner's
    own estimate for comparison, a human-readable reason, and remaining work.

Both take an already-feature-engineered task row (one row of the DataFrame
`src.features.build_features.build_task_level_dataset()` produces) — this
module does not re-run the feature pipeline itself, so callers control
exactly which data (and which `as_of` cutoff) feeds the model.
"""

import pandas as pd

from src.eta.explain import build_eta_explanation
from src.eta.model_io import EtaModelBundle, load_eta_model
from src.eta.remaining_work import calculate_remaining_work


MIN_ETA_MIN = 1.0  # a task can't logically take less than ~1 minute; also the floor used below


def predict_eta(task_features: pd.Series, model_bundle: EtaModelBundle | None = None) -> float:
    """Point prediction only (minutes). The simplest possible call.

    Floored at `MIN_ETA_MIN`: a linear model has no output bound, so a
    sufficiently out-of-distribution input (e.g. near-zero estimated
    buckets/volume) can otherwise predict a negative duration. Every other
    ETA number (personalized range, dynamic ETA) is derived from this call,
    so flooring it here fixes the root cause everywhere at once.
    """
    bundle = model_bundle or load_eta_model()
    X = task_features[bundle.feature_columns].to_frame().T
    raw = float(bundle.model.predict(X)[0])
    return max(MIN_ETA_MIN, raw)


def predict_personalized_eta(
    task_features: pd.Series,
    operator_twin: dict,
    telemetry_so_far: pd.DataFrame | None = None,
    model_bundle: EtaModelBundle | None = None,
) -> dict:
    """Full personalized ETA result for a task that hasn't started yet (or
    is being viewed pre-task, e.g. on the Mission Board / Pre-Task Briefing).

    Returns exactly the shape the product spec asks for:
        {eta_min, eta_max, original_eta, reason, buckets_remaining}
    plus the point estimate and structured factors for anyone who wants more
    than the headline reason string.
    """
    bundle = model_bundle or load_eta_model()
    point = predict_eta(task_features, bundle)

    q = bundle.residual_quantile_offsets
    eta_min = max(MIN_ETA_MIN, point + q["q_low"])
    eta_max = max(eta_min, point + q["q_high"])
    # Defensive: the point estimate must lie within its own reported range.
    # This is structurally true whenever q_high >= 0 (the usual case), but
    # not guaranteed if a future retrain ever produces a negative q_high
    # (systematic over-prediction on the validation set) — clamp explicitly
    # rather than relying on that being true by luck of the current data.
    point = min(max(point, eta_min), eta_max)

    remaining = calculate_remaining_work(task_features, telemetry_so_far)

    weather_row = {"condition": task_features.get("weather")}
    explanation = build_eta_explanation(task_features.to_dict(), operator_twin, weather_row=weather_row)

    return {
        "eta_min": round(eta_min, 1),
        "eta_max": round(eta_max, 1),
        "eta_point": round(point, 1),
        "original_eta": round(float(task_features["estimated_time_min"]), 1),
        "reason": explanation["reason"],
        "factors": explanation["factors"],
        "buckets_remaining": remaining["buckets_remaining"],
        "model_name": bundle.model_name,
    }
