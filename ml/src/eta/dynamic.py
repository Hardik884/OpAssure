"""Dynamic (in-progress) ETA: recompute a running task's ETA from its own
telemetry so far, instead of just returning the pre-task prediction.

Deliberately rule-based, not a second trained model — the inputs (elapsed
time, recent cycle time vs. the pace implied by the original prediction,
remaining buckets) are exactly what the product spec asks for, and a rule
here is easier to explain and trust mid-shift than a black-box re-prediction.
The uncertainty interval still comes from the same validated residual
quantiles as the baseline model, just scaled down as the task nears
completion (less work left -> less that can still go wrong).
"""

import pandas as pd

from src.common import config
from src.eta.explain import build_eta_explanation
from src.eta.model_io import EtaModelBundle, load_eta_model
from src.eta.remaining_work import calculate_remaining_work


def _elapsed_minutes(task_features: pd.Series, telemetry_so_far: pd.DataFrame) -> float:
    if len(telemetry_so_far) == 0:
        return 0.0
    last_ts = pd.to_datetime(telemetry_so_far["timestamp"]).max()
    start_ts = pd.to_datetime(task_features["start_time"])
    return max(0.0, (last_ts - start_ts).total_seconds() / 60.0 + config.TELEMETRY_INTERVAL_MIN)


def _recent_cycle_time_s(telemetry_so_far: pd.DataFrame) -> float | None:
    moving = telemetry_so_far[telemetry_so_far["machine_moving"]]
    if len(moving) == 0:
        return None
    recent = moving.sort_values("timestamp").tail(config.RECENT_TELEMETRY_ROWS)
    recent = recent[recent["avg_cycle_time_s"] > 0]
    if len(recent) == 0:
        return None
    return float(recent["avg_cycle_time_s"].mean())


def predict_dynamic_eta(
    task_features: pd.Series,
    telemetry_so_far: pd.DataFrame,
    operator_twin: dict,
    original_point_eta_min: float | None = None,
    model_bundle: EtaModelBundle | None = None,
) -> dict:
    """Recompute ETA for a task that's already running.

    `original_point_eta_min` is the pre-task point prediction from
    `predict_eta` — pass it in if you already have it (e.g. from Mission
    Board) to avoid re-predicting; otherwise it's computed here.
    """
    bundle = model_bundle or load_eta_model()
    if original_point_eta_min is None:
        from src.eta.inference import predict_eta

        original_point_eta_min = predict_eta(task_features, bundle)

    remaining = calculate_remaining_work(task_features, telemetry_so_far)
    elapsed_min = _elapsed_minutes(task_features, telemetry_so_far)

    total_buckets = remaining["total_buckets"]
    planned_cycle_time_s = (original_point_eta_min * 60.0) / total_buckets if total_buckets > 0 else 30.0

    recent_cycle_time_s = _recent_cycle_time_s(telemetry_so_far)
    cycle_time_change_pct = None
    if recent_cycle_time_s is not None and planned_cycle_time_s > 0:
        cycle_time_change_pct = (recent_cycle_time_s / planned_cycle_time_s) - 1.0
        effective_cycle_time_s = recent_cycle_time_s
    else:
        effective_cycle_time_s = planned_cycle_time_s

    remaining_time_min = remaining["buckets_remaining"] * effective_cycle_time_s / 60.0
    point = elapsed_min + remaining_time_min

    # Uncertainty shrinks as the task nears completion — there's less
    # remaining work left for reality to diverge from the estimate on.
    remaining_fraction = remaining["buckets_remaining"] / total_buckets if total_buckets > 0 else 0.0
    q = bundle.residual_quantile_offsets
    eta_min = max(elapsed_min, point + q["q_low"] * remaining_fraction)
    eta_max = max(eta_min, point + q["q_high"] * remaining_fraction)
    # Defensive, same reasoning as predict_personalized_eta(): keep the
    # point estimate inside its own reported range regardless of the sign
    # of q_high (not structurally guaranteed if a future retrain ever
    # produces a negative one).
    point = min(max(point, eta_min), eta_max)

    weather_row = {"condition": task_features.get("weather")}
    explanation = build_eta_explanation(
        task_features.to_dict(),
        operator_twin,
        weather_row=weather_row,
        cycle_time_change_pct=cycle_time_change_pct,
    )

    return {
        "eta_min": round(eta_min, 1),
        "eta_max": round(eta_max, 1),
        "eta_point": round(point, 1),
        "original_eta": round(float(original_point_eta_min), 1),
        "reason": explanation["reason"],
        "factors": explanation["factors"],
        "buckets_remaining": remaining["buckets_remaining"],
        "pct_complete": remaining["pct_complete"],
        "cycle_time_change_pct": None if cycle_time_change_pct is None else round(cycle_time_change_pct, 3),
    }
