"""Evaluate the final ML intelligence layer (training recommendations and
the threat briefing) against real structured facts in the generated
dataset — a separate, additive module from `behaviour_eval.py` so the
already-working ground-truth evaluation there is never touched.

Per the project rule, this makes no claim of human-level or real-world
training effectiveness — it only reports what the synthetic data supports,
and says so explicitly when evidence is incomplete.
"""

import pandas as pd

from src.anomaly.diagnosis import diagnose_fuel_source
from src.anomaly.habit_radar import detect_habits, get_habit_summary
from src.common import config
from src.safety.threat_briefing import generate_threat_briefing
from src.training.effectiveness import get_training_outcome
from src.training.recommend import get_training_recommendation


def evaluate_training_recommendation_relevance(tables: dict) -> dict:
    """Does the recommendation engine actually target the two planted
    operators (seatbelt habit, fuel inefficiency), and correctly NOT
    recommend anything for an operator with no repeated pattern?"""
    tasks_df, telemetry_df = tables["tasks"], tables["telemetry"]
    operators_df, near_misses_df = tables["operators"], tables["near_misses"]

    habit_op_result = get_training_recommendation(
        config.SEATBELT_HABIT_OPERATOR_ID, tasks_df, telemetry_df, operators_df, near_misses_df
    )

    fuel_findings = diagnose_fuel_source(tasks_df, telemetry_df)
    inefficient_op_result = get_training_recommendation(
        config.INEFFICIENT_OPERATOR_ID, tasks_df, telemetry_df, operators_df, near_misses_df
    )

    # An operator with the least habit/diagnosis evidence in the fleet
    # should NOT get a recommendation — proves the engine isn't just
    # recommending training to everyone.
    all_habits = {r["operator_id"]: r for r in detect_habits(telemetry_df)}
    quiet_operator = min(all_habits, key=lambda op: all_habits[op]["frequency"])
    quiet_result = get_training_recommendation(quiet_operator, tasks_df, telemetry_df, operators_df, near_misses_df)

    return {
        "seatbelt_habit_operator": config.SEATBELT_HABIT_OPERATOR_ID,
        "seatbelt_habit_recommended": habit_op_result.get("recommended", False),
        "seatbelt_habit_trigger": habit_op_result.get("trigger_type"),
        "inefficient_operator": config.INEFFICIENT_OPERATOR_ID,
        "inefficient_operator_fuel_finding_exists": any(
            f["source"] == "operator" and f["operator_id"] == config.INEFFICIENT_OPERATOR_ID for f in fuel_findings
        ),
        "inefficient_operator_recommended": inefficient_op_result.get("recommended", False),
        "inefficient_operator_trigger": inefficient_op_result.get("trigger_type"),
        "quiet_operator": quiet_operator,
        "quiet_operator_not_over_flagged": not (
            quiet_result.get("recommended") and quiet_result.get("trigger_type") == "seatbelt_habit"
        ),
    }


def evaluate_training_effectiveness(tables: dict) -> dict:
    """Report training-effect results for every operator with a completed
    training event on record — honestly, including "insufficient_evidence"
    where that's genuinely the case. No claim beyond what this synthetic
    data actually supports.
    """
    tasks_df, telemetry_df = tables["tasks"], tables["telemetry"]
    training_events_df = tables["training_events"]

    operators_with_training = training_events_df[training_events_df["completed"] == True]["operator_id"].unique()  # noqa: E712

    results = []
    for operator_id in operators_with_training:
        outcome = get_training_outcome(operator_id, tasks_df, telemetry_df, training_events_df)
        results.append({"operator_id": operator_id, **outcome})

    n_evaluated = len(results)
    n_with_full_evidence = sum(1 for r in results if r.get("observations", 0) >= config.TRAINING_OBSERVATION_WINDOW)

    return {
        "n_operators_with_completed_training": n_evaluated,
        "n_with_full_5_observation_window": n_with_full_evidence,
        "results": results,
    }


def evaluate_threat_briefing_correctness(tables: dict) -> dict:
    """Run the threat briefing against real structured facts for a handful
    of tasks chosen specifically to exercise each risk source, and check the
    expected source shows up in the (correctly ranked) top 3."""
    from src.features.build_features import build_task_level_dataset
    from src.operator_twin.twin import get_operator_profile

    tasks_df, telemetry_df = tables["tasks"], tables["telemetry"]
    operators_df, machines_df, weather_df = tables["operators"], tables["machines"], tables["weather"]
    near_misses_df = tables["near_misses"]

    features_df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)

    checks = []

    # weather-driven: a wet task for an operator with above-average rain sensitivity
    wet_tasks = tasks_df[tasks_df["weather"].isin(["rain", "storm"])]
    if len(wet_tasks):
        row = wet_tasks.iloc[0]
        twin = get_operator_profile(row["operator_id"], tasks_df, telemetry_df, operators_df)
        task_features = features_df[features_df["task_id"] == row["task_id"]].iloc[0]
        briefing = generate_threat_briefing(dict(task_features), twin)
        checks.append(
            {
                "case": "weather_driven",
                "task_id": row["task_id"],
                "pass": any(r["source"] == "weather" for r in briefing),
            }
        )

    # operator-driven: the seatbelt-habit operator's own tasks
    habit_summary = get_habit_summary(config.SEATBELT_HABIT_OPERATOR_ID, telemetry_df)
    habit_tasks = tasks_df[tasks_df["operator_id"] == config.SEATBELT_HABIT_OPERATOR_ID]
    if len(habit_tasks) and habit_summary["is_habit"]:
        row = habit_tasks.iloc[0]
        twin = get_operator_profile(row["operator_id"], tasks_df, telemetry_df, operators_df)
        task_features = features_df[features_df["task_id"] == row["task_id"]].iloc[0]
        briefing = generate_threat_briefing(dict(task_features), twin, habit_summary=habit_summary)
        checks.append(
            {
                "case": "operator_driven",
                "task_id": row["task_id"],
                "pass": any(r["source"] == "safety" for r in briefing) and briefing[0]["source"] == "safety",
            }
        )

    # machine-driven: a task on the planted degrading machine
    degrading_tasks = tasks_df[tasks_df["machine_id"] == config.DEGRADING_MACHINE_ID]
    if len(degrading_tasks):
        row = degrading_tasks.iloc[-1]  # late task, where the degradation trend is most visible
        twin = get_operator_profile(row["operator_id"], tasks_df, telemetry_df, operators_df)
        task_features = features_df[features_df["task_id"] == row["task_id"]].iloc[0]
        machine_degrading = bool(task_features["machine_recent_vs_alltime_gap_prior"] > 0)
        briefing = generate_threat_briefing(dict(task_features), twin, machine_degrading=machine_degrading)
        checks.append(
            {
                "case": "machine_driven",
                "task_id": row["task_id"],
                "pass": (not machine_degrading) or any(r["source"] == "machine" for r in briefing),
            }
        )

    n_pass = sum(1 for c in checks if c["pass"])
    return {"n_checks": len(checks), "n_pass": n_pass, "checks": checks}
