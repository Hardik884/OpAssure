"""The single high-level entry point: `generate_operator_state()`.

This module does not implement any model or rule itself — it only loads
data once, calls the already-built modules in the right order (passing each
one's output into the next where needed, e.g. the Operator Twin into ETA,
Focus, and the threat briefing), and assembles one combined result. See
`ml/docs/integration.md` for the backend-facing contract.
"""

import pandas as pd

from src.anomaly.diagnosis import diagnose_fuel_source
from src.anomaly.habit_radar import get_habit_summary
from src.anomaly.idle_shield import classify_task_idle
from src.common import config
from src.common.loaders import (
    load_machines,
    load_near_misses,
    load_operators,
    load_task_ground_truth,
    load_tasks,
    load_telemetry,
    load_weather,
)
from src.eta.dynamic import predict_dynamic_eta
from src.eta.inference import predict_personalized_eta
from src.eta.model_io import load_eta_model
from src.eta.remaining_work import calculate_remaining_work
from src.features.build_features import build_task_level_dataset
from src.intelligence import explanations as ex
from src.operator_twin.twin import get_operator_profile
from src.safety.focus_battery import calculate_focus, get_focus_recommendation
from src.safety.risk import calculate_risk
from src.safety.threat_briefing import generate_threat_briefing
from src.training.recommend import recommend_training


def _load_tables() -> dict:
    return {
        "operators": load_operators(),
        "machines": load_machines(),
        "weather": load_weather(),
        "tasks": load_tasks(),
        "telemetry": load_telemetry(),
        "near_misses": load_near_misses(),
    }


def generate_operator_state(
    operator_id: str,
    machine_id: str,
    task_id: str,
    current_context: dict | None = None,
    tables: dict | None = None,
    features_df: pd.DataFrame | None = None,
) -> dict:
    """Build the full unified intelligence result for one operator/machine/task.

    `current_context` (all optional):
      - `as_of` (Timestamp): point in time to evaluate Focus Battery at.
        Defaults to the task's own start_time.
      - `telemetry_so_far` (DataFrame): telemetry recorded for this task so
        far. Defaults to empty (a not-yet-started task) — pass the real
        telemetry for an in-progress task to get a genuine dynamic ETA.

    `tables` lets a caller (e.g. `update_operator_state`, or a backend that
    keeps its own cache) pass already-loaded DataFrames instead of hitting
    disk again — safe to omit for a one-off call.

    `features_df` (performance): `build_task_level_dataset()` recomputes
    expanding-window historical features across the ENTIRE tasks table —
    the dominant cost of this function (a few seconds on the full synthetic
    dataset), independent of `tables` reuse. A caller making multiple calls
    in the same session (e.g. a fleet dashboard, or a demo stepping through
    several operators) should build it once —
    `src.features.build_features.build_task_level_dataset(tasks_df,
    operators_df, machines_df, weather_df, telemetry_df)` — and pass it here
    on every subsequent call. Safe to omit for a one-off call.
    """
    context = current_context or {}
    tables = tables or _load_tables()

    operators_df, machines_df, weather_df = tables["operators"], tables["machines"], tables["weather"]
    tasks_df, telemetry_df, near_misses_df = tables["tasks"], tables["telemetry"], tables["near_misses"]

    if operator_id not in set(operators_df["operator_id"]):
        raise ValueError(f"Unknown operator_id '{operator_id}'")
    if machine_id not in set(machines_df["machine_id"]):
        raise ValueError(f"Unknown machine_id '{machine_id}'")

    task_rows = tasks_df[tasks_df["task_id"] == task_id]
    if len(task_rows) == 0:
        raise ValueError(f"Unknown task_id '{task_id}'")
    task_row = task_rows.iloc[0]

    if task_row["machine_id"] != machine_id:
        raise ValueError(
            f"machine_id '{machine_id}' does not match task '{task_id}''s actual machine "
            f"('{task_row['machine_id']}') — this would silently produce an inconsistent state "
            "(ETA computed for the real machine, diagnosis/briefing filtered to the wrong one)."
        )
    if task_row["operator_id"] != operator_id:
        raise ValueError(
            f"operator_id '{operator_id}' does not match task '{task_id}''s actual operator "
            f"('{task_row['operator_id']}')."
        )

    # Default to a genuinely empty ("not started yet") telemetry window — a
    # task's very first telemetry row is recorded exactly AT start_time, so
    # filtering by `timestamp <= start_time` would silently include real
    # progress instead of representing "before the task has begun".
    telemetry_so_far = context.get("telemetry_so_far")
    if telemetry_so_far is None:
        telemetry_so_far = telemetry_df.iloc[0:0]  # empty, but with the right columns/dtypes
    as_of = context.get("as_of", task_row["start_time"])

    # --- Operator Twin (used by ETA, Focus, and the threat briefing below) ---
    twin = get_operator_profile(operator_id, tasks_df, telemetry_df, operators_df)

    # --- ETA (baseline + personalized) ---------------------------------------
    if features_df is None:
        features_df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    task_features_rows = features_df[features_df["task_id"] == task_id]
    if len(task_features_rows) == 0:
        raise ValueError(f"Task '{task_id}' produced no feature row — cannot compute ETA.")
    task_features = task_features_rows.iloc[0]

    eta_bundle = load_eta_model()
    eta_result = predict_personalized_eta(task_features, twin, telemetry_so_far=telemetry_so_far, model_bundle=eta_bundle)
    dynamic_eta = predict_dynamic_eta(
        task_features, telemetry_so_far, twin, original_point_eta_min=eta_result["eta_point"], model_bundle=eta_bundle
    )
    remaining_work = calculate_remaining_work(task_features, telemetry_so_far)

    # --- Habit Radar / Idle Shield -------------------------------------------
    habit_summary = get_habit_summary(operator_id, telemetry_df)
    idle_analysis = classify_task_idle(task_id, telemetry_df)

    # --- Focus Battery ----------------------------------------------------------
    focus = get_focus_recommendation(calculate_focus(operator_id, as_of, tasks_df, weather_df, twin))

    # --- Risk intelligence -------------------------------------------------------
    last_row = telemetry_so_far.iloc[-1] if len(telemetry_so_far) else None
    task_near_misses = near_misses_df[near_misses_df["task_id"] == task_id]
    nearest_distance = float(task_near_misses["distance_m"].min()) if len(task_near_misses) else None
    recent_safety_alert_count = int(telemetry_so_far["safety_alert"].sum()) if len(telemetry_so_far) else 0
    machine_degrading = bool(task_features["machine_recent_vs_alltime_gap_prior"] > 0)

    risk = calculate_risk(
        seatbelt_status=last_row["seatbelt_status"] if last_row is not None else "buckled",
        machine_moving=bool(last_row["machine_moving"]) if last_row is not None else False,
        nearest_worker_distance_m=nearest_distance,
        recent_safety_alert_count=recent_safety_alert_count,
        weather_condition=task_row["weather"],
        persistent_habit=habit_summary["is_habit"],
        machine_degrading=machine_degrading,
    )

    # --- Machine-vs-operator fuel diagnosis (filtered to this operator/machine) -
    all_diagnosis = diagnose_fuel_source(tasks_df, telemetry_df)
    fuel_diagnosis = [
        f
        for f in all_diagnosis
        if (f["source"] == "operator" and f.get("operator_id") == operator_id)
        or (f["source"] == "machine" and f.get("machine_id") == machine_id)
    ]
    operator_fuel_finding = next((f for f in fuel_diagnosis if f["source"] == "operator"), None)

    # --- Just-in-Time Micro Training -------------------------------------------
    operator_task_ids = set(tasks_df[tasks_df["operator_id"] == operator_id]["task_id"])
    proximity_event_count = int(near_misses_df[near_misses_df["task_id"].isin(operator_task_ids)].shape[0])
    training = recommend_training(
        habit_summary=habit_summary,
        proximity_event_count=proximity_event_count,
        fuel_finding=operator_fuel_finding,
        operator_twin=twin,
    )

    # --- Pre-Task Threat Briefing ------------------------------------------------
    site_near_miss_count = int((near_misses_df["machine_id"] == machine_id).sum())
    briefing_task_row = dict(task_row)
    briefing_task_row["temperature"] = float(task_features.get("temperature", None)) if "temperature" in task_features else None
    briefing_task_row["hour_of_day"] = float(task_features.get("hour_of_day", None)) if "hour_of_day" in task_features else None
    threat_briefing = generate_threat_briefing(
        briefing_task_row,
        twin,
        habit_summary=habit_summary,
        machine_degrading=machine_degrading,
        recent_safety_alert_count=recent_safety_alert_count,
        site_near_miss_count=site_near_miss_count,
    )

    # --- Structured explanations ------------------------------------------------
    explanations_out = {
        "eta": ex.explain_eta(eta_result),
        "operator_twin": ex.explain_operator_twin(twin),
        "habits": ex.explain_habit(habit_summary),
        "idle_analysis": ex.explain_idle(idle_analysis),
        "focus": ex.explain_focus(focus),
        "risk": ex.explain_risk(risk),
        "fuel_diagnosis": ex.explain_diagnosis(fuel_diagnosis),
        "training": ex.explain_training(training),
        "threat_briefing": ex.explain_threat_briefing(threat_briefing),
    }

    return {
        "operator_id": operator_id,
        "machine_id": machine_id,
        "task_id": task_id,
        "operator_twin": twin,
        "eta": eta_result,
        "dynamic_eta": dynamic_eta,
        "remaining_work": remaining_work,
        "risk": risk,
        "habits": [habit_summary],
        "idle_analysis": idle_analysis,
        "focus": focus,
        "fuel_diagnosis": fuel_diagnosis,
        "training": training,
        "threat_briefing": threat_briefing,
        "explanations": explanations_out,
        # Internal cache for update_operator_state() — not part of the
        # public contract, but keeps a realtime update from reloading
        # disk or recomputing the model bundle/features/twin from scratch.
        "_context": {
            "tables": tables,
            "features_df": features_df,
            "task_features": task_features,
            "eta_bundle": eta_bundle,
            "telemetry_so_far": telemetry_so_far,
            "task_row": task_row,
        },
    }
