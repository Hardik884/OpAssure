"""Fast, no-retraining realtime updates for an active task.

`update_operator_state()` takes the state `generate_operator_state()`
returned (which carries a small internal `_context` cache: the loaded
tables, the cached ETA model bundle, the task's feature row, and the
telemetry recorded so far) and a single new telemetry row, and recomputes
ONLY what a new telemetry reading can actually change: dynamic ETA,
remaining work, risk, Focus, and — only when this row actually completes a
truck-wait idle->moving transition — the habit count/summary. Nothing here
retrains a model or reloads data from disk.
"""

import pandas as pd

from src.anomaly.habit_radar import get_habit_summary
from src.eta.dynamic import predict_dynamic_eta
from src.eta.remaining_work import calculate_remaining_work
from src.intelligence import explanations as ex
from src.safety.focus_battery import calculate_focus, get_focus_recommendation
from src.safety.risk import calculate_risk
from src.training.recommend import recommend_training


def _completes_truck_wait_transition(previous_telemetry: pd.DataFrame, new_row: dict) -> bool:
    if not new_row.get("machine_moving") or len(previous_telemetry) == 0:
        return False
    last = previous_telemetry.sort_values("timestamp").iloc[-1]
    return bool((not last["machine_moving"]) and last["idle_reason"] == "waiting_for_truck")


def update_operator_state(
    previous_state: dict,
    new_telemetry: dict,
    weather_row: dict | None = None,
    task_context: dict | None = None,
) -> dict:
    """Return a new state dict reflecting one new telemetry reading.

    `new_telemetry` is a single telemetry row as a dict (same fields as the
    `telemetry` table). `task_context` may override `nearest_worker_distance_m`
    for this tick (e.g. from a live worker-position feed) — everything else
    not explicitly updatable here is carried forward unchanged from
    `previous_state`.
    """
    if "_context" not in previous_state:
        raise ValueError(
            "previous_state has no _context cache — pass the dict returned by "
            "generate_operator_state(), not a re-serialized copy of it."
        )

    ctx = previous_state["_context"]
    task_context = task_context or {}

    old_telemetry_so_far = ctx["telemetry_so_far"]
    new_row_df = pd.DataFrame([new_telemetry])
    updated_telemetry_so_far = pd.concat([old_telemetry_so_far, new_row_df], ignore_index=True, sort=False)

    task_features = ctx["task_features"]
    eta_bundle = ctx["eta_bundle"]
    twin = previous_state["operator_twin"]  # not recomputed every tick — see module docstring

    # --- Dynamic ETA + remaining work (cheap, always recomputed) -------------
    dynamic_eta = predict_dynamic_eta(
        task_features,
        updated_telemetry_so_far,
        twin,
        original_point_eta_min=previous_state["eta"]["eta_point"],
        model_bundle=eta_bundle,
    )
    remaining_work = calculate_remaining_work(task_features, updated_telemetry_so_far)

    # --- Risk (cheap, always recomputed from the latest row) -----------------
    recent_safety_alert_count = int(updated_telemetry_so_far["safety_alert"].sum())
    risk = calculate_risk(
        seatbelt_status=new_telemetry.get("seatbelt_status", "buckled"),
        machine_moving=bool(new_telemetry.get("machine_moving", False)),
        nearest_worker_distance_m=task_context.get("nearest_worker_distance_m"),
        recent_safety_alert_count=recent_safety_alert_count,
        weather_condition=(weather_row or {}).get("condition", task_features.get("weather")),
        persistent_habit=previous_state["habits"][0]["is_habit"],
        machine_degrading=bool(task_features["machine_recent_vs_alltime_gap_prior"] > 0),
    )

    # --- Habit state: only recomputed when this row actually completes an
    # opportunity (a truck-wait idle block resolving into movement) — not on
    # every routine tick, which is what keeps this update path fast. -------
    habit_summary = previous_state["habits"][0]
    if _completes_truck_wait_transition(old_telemetry_so_far, new_telemetry):
        tables = ctx["tables"]
        task_id = previous_state["task_id"]
        combined_telemetry = pd.concat(
            [tables["telemetry"][tables["telemetry"]["task_id"] != task_id], updated_telemetry_so_far],
            ignore_index=True,
            sort=False,
        )
        habit_summary = get_habit_summary(previous_state["operator_id"], combined_telemetry)

    # --- Focus (cheap — small per-operator task slice + one weather lookup) --
    as_of = pd.to_datetime(new_telemetry.get("timestamp", ctx["task_row"]["start_time"]))
    focus = get_focus_recommendation(
        calculate_focus(previous_state["operator_id"], as_of, ctx["tables"]["tasks"], ctx["tables"]["weather"], twin)
    )

    # --- Training recommendation (cheap — reuses the cached fuel diagnosis,
    # no full-fleet diagnosis re-scan on every tick) --------------------------
    operator_fuel_finding = next(
        (f for f in previous_state["fuel_diagnosis"] if f.get("source") == "operator"), None
    )
    proximity_event_count = sum(
        1 for r in previous_state["threat_briefing"] if r["source"] == "site"
    )  # unchanged mid-task; a real proximity re-count would need live worker positions
    training = recommend_training(
        habit_summary=habit_summary,
        proximity_event_count=proximity_event_count,
        fuel_finding=operator_fuel_finding,
        operator_twin=twin,
    )

    new_state = dict(previous_state)
    new_state.update(
        {
            "dynamic_eta": dynamic_eta,
            "remaining_work": remaining_work,
            "risk": risk,
            "habits": [habit_summary],
            "focus": focus,
            "training": training,
            "explanations": {
                **previous_state["explanations"],
                "risk": ex.explain_risk(risk),
                "habits": ex.explain_habit(habit_summary),
                "focus": ex.explain_focus(focus),
                "training": ex.explain_training(training),
            },
            "_context": {**ctx, "telemetry_so_far": updated_telemetry_so_far},
        }
    )
    return new_state
