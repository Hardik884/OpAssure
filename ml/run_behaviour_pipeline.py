#!/usr/bin/env python
"""OpAssure Behaviour + Safety Intelligence — single entry point.

Usage (from the repo root or from `ml/`):

    python ml/run_behaviour_pipeline.py

Runs Habit Radar, Idle Shield, Focus Battery, risk intelligence, and the
machine-vs-operator fuel diagnosis for the deterministic demo scenario
(OP1001 / EXC001 / T001), then evaluates all of them against
`data/ground_truth/`. Reuses the existing feature pipeline, loaders, and
Operator Twin as-is — this script only wires the new modules together.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.anomaly.diagnosis import diagnose_fuel_source  # noqa: E402
from src.anomaly.habit_radar import get_habit_summary  # noqa: E402
from src.anomaly.idle_shield import classify_task_idle  # noqa: E402
from src.common import config  # noqa: E402
from src.common.loaders import (  # noqa: E402
    load_machines,
    load_near_misses,
    load_operators,
    load_task_ground_truth,
    load_tasks,
    load_telemetry,
    load_weather,
)
from src.evaluation.behaviour_eval import evaluate_all  # noqa: E402
from src.features.build_features import build_task_level_dataset  # noqa: E402
from src.operator_twin.twin import get_operator_profile  # noqa: E402
from src.safety.focus_battery import calculate_focus, get_focus_recommendation  # noqa: E402
from src.safety.risk import calculate_risk  # noqa: E402


def run_demo() -> None:
    print("\n" + "=" * 70)
    print(f"BEHAVIOUR + SAFETY DEMO: {config.DEMO_OPERATOR_ID} / {config.DEMO_MACHINE_ID} / {config.DEMO_TASK_ID}")
    print("=" * 70)

    operators_df = load_operators()
    machines_df = load_machines()
    weather_df = load_weather()
    tasks_df = load_tasks()
    telemetry_df = load_telemetry()
    near_misses_df = load_near_misses()

    demo_task = tasks_df[tasks_df["task_id"] == config.DEMO_TASK_ID].iloc[0]
    demo_telemetry = telemetry_df[telemetry_df["task_id"] == config.DEMO_TASK_ID].sort_values("timestamp")

    # --- 1. Habit Radar -----------------------------------------------------
    habit = get_habit_summary(config.DEMO_OPERATOR_ID, telemetry_df)
    print(f"\n1) Habit Radar for {config.DEMO_OPERATOR_ID}:")
    for k, v in habit.items():
        print(f"   {k:<18} {v}")

    # --- 2. Idle Shield -------------------------------------------------------
    idle_result = classify_task_idle(config.DEMO_TASK_ID, telemetry_df)
    print(f"\n2) Idle Shield for task {config.DEMO_TASK_ID}:")
    for k, v in idle_result.items():
        print(f"   {k:<20} {v}")

    # --- 3. Focus Battery -------------------------------------------------------
    twin = get_operator_profile(config.DEMO_OPERATOR_ID, tasks_df, telemetry_df, operators_df)
    focus_raw = calculate_focus(
        config.DEMO_OPERATOR_ID, demo_task["start_time"], tasks_df, weather_df, twin
    )
    focus = get_focus_recommendation(focus_raw)
    print(f"\n3) Focus Battery for {config.DEMO_OPERATOR_ID} at {demo_task['start_time']}:")
    print(f"   score: {focus['score']}")
    print(f"   factors: {focus['factors']}")
    print(f"   recommendation: {focus['recommendation']}")
    print(f"   disclaimer: {focus['disclaimer']}")

    # --- 4. Risk intelligence ----------------------------------------------
    demo_near_misses = near_misses_df[near_misses_df["task_id"] == config.DEMO_TASK_ID]
    nearest_distance = float(demo_near_misses["distance_m"].min()) if len(demo_near_misses) else None
    recent_alerts = int(demo_telemetry["safety_alert"].sum())

    features_df = build_task_level_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    demo_features = features_df[features_df["task_id"] == config.DEMO_TASK_ID].iloc[0]
    machine_degrading = bool(demo_features["machine_recent_vs_alltime_gap_prior"] > 0)

    last_row = demo_telemetry.iloc[-1] if len(demo_telemetry) else None
    risk = calculate_risk(
        seatbelt_status=last_row["seatbelt_status"] if last_row is not None else "buckled",
        machine_moving=bool(last_row["machine_moving"]) if last_row is not None else False,
        nearest_worker_distance_m=nearest_distance,
        recent_safety_alert_count=recent_alerts,
        weather_condition=demo_task["weather"],
        persistent_habit=habit["is_habit"],
        machine_degrading=machine_degrading,
    )
    print(f"\n4) Risk intelligence for task {config.DEMO_TASK_ID}:")
    for k, v in risk.items():
        print(f"   {k:<20} {v}")

    # --- 5. Machine vs. operator diagnosis ----------------------------------
    diagnosis = diagnose_fuel_source(tasks_df, telemetry_df)
    print(f"\n5) Machine vs. operator fuel diagnosis ({len(diagnosis)} finding(s)):")
    for f in diagnosis:
        print(f"   {f}")

    print("\nDemo inference completed with no errors.\n")


def run_evaluation() -> None:
    print("=" * 70)
    print("GROUND-TRUTH EVALUATION")
    print("=" * 70)

    tables = {
        "operators": load_operators(),
        "machines": load_machines(),
        "weather": load_weather(),
        "tasks": load_tasks(),
        "telemetry": load_telemetry(),
        "task_ground_truth": load_task_ground_truth(),
    }
    report = evaluate_all(tables)

    print("\nHabit Radar:")
    hr = report["habit_radar"]
    print(f"   flagged_operators:   {hr['flagged_operators']}")
    print(f"   expected_operator:   {hr['expected_operator']}")
    print(f"   correctly_flagged:   {hr['correctly_flagged']}")
    print(f"   false_positives:     {hr['n_false_positives']}")
    print(f"   precision/recall/f1: {hr['precision']}/{hr['recall']}/{hr['f1']}")

    print("\nIdle Shield:")
    idl = report["idle_shield"]
    print(f"   n_tasks_evaluated:   {idl['n_tasks_evaluated']}")
    print(f"   accuracy:            {idl['accuracy']}")
    print(f"   precision/recall/f1: {idl['precision']}/{idl['recall']}/{idl['f1']}")
    print(f"   truck_wait_tasks:    {idl['truck_wait_tasks_evaluated']}")
    print(
        f"   legitimate idle falsely blamed on operator: "
        f"{idl['legitimate_idle_falsely_blamed_count']} / {idl['truck_wait_tasks_evaluated']} "
        f"({idl['legitimate_idle_falsely_blamed_rate']:.1%})"
    )

    print("\nMachine vs. operator diagnosis:")
    dx = report["diagnosis"]
    print(f"   machine_correctly_flagged:  {dx['machine_correctly_flagged']} (expected {dx['expected_machine']})")
    print(f"   operator_correctly_flagged: {dx['operator_correctly_flagged']} (expected {dx['expected_operator']})")
    print(f"   false positives: machine={dx['n_machine_false_positives']}  operator={dx['n_operator_false_positives']}")

    print("\nSeatbelt critical-risk detection (sanity check vs. telemetry's own safety_alert):")
    sc = report["seatbelt_critical_detection"]
    print(f"   n_sampled={sc['n_sampled']}  precision={sc['precision']}  recall={sc['recall']}  f1={sc['f1']}")
    print()


def main() -> None:
    run_evaluation()
    run_demo()


if __name__ == "__main__":
    main()
