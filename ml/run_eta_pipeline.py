#!/usr/bin/env python
"""OpAssure ETA + Operator Twin — single entry point.

Usage (from the repo root or from `ml/`):

    python ml/run_eta_pipeline.py                # train if no model saved yet, then run the demo
    python ml/run_eta_pipeline.py --train         # force-retrain the ETA model first
    python ml/run_eta_pipeline.py --demo-only     # skip training, just run inference (fails if no model saved)

Reuses the existing feature pipeline, loaders, and synthetic data as-is —
this script only adds the ETA model layer on top and demonstrates it for
the deterministic demo scenario (OP1001 / EXC001 / T001).
"""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.common import config  # noqa: E402
from src.common.loaders import load_machines, load_operators, load_tasks, load_telemetry, load_weather  # noqa: E402
from src.eta.dataset import build_eta_dataset  # noqa: E402
from src.eta.dynamic import predict_dynamic_eta  # noqa: E402
from src.eta.inference import predict_eta, predict_personalized_eta  # noqa: E402
from src.eta.model_io import eta_model_exists, load_eta_model  # noqa: E402
from src.eta.remaining_work import calculate_remaining_work  # noqa: E402
from src.eta.train import train_and_select  # noqa: E402
from src.operator_twin.twin import get_operator_profile  # noqa: E402


def print_report(report: dict) -> None:
    print(f"Split sizes: {report['split_sizes']}")
    print("\nCandidate comparison (validation set):")
    for name, scores in report["candidates"].items():
        v = scores["val"]
        marker = "  <- selected" if name == report["selected_model"] else ""
        print(f"  {name:<18} MAE={v['mae']:6.2f}  RMSE={v['rmse']:6.2f}  median_AE={v['median_ae']:6.2f}{marker}")
    best = report["candidates"][report["selected_model"]]
    t = best["test"]
    print(f"\nSelected model: {report['selected_model']}")
    print(f"Held-out test performance: MAE={t['mae']:.2f}  RMSE={t['rmse']:.2f}  median_AE={t['median_ae']:.2f} (min)")


def run_demo() -> None:
    print("\n" + "=" * 70)
    print(f"DEMO INFERENCE: {config.DEMO_OPERATOR_ID} / {config.DEMO_MACHINE_ID} / {config.DEMO_TASK_ID}")
    print("=" * 70)

    operators_df = load_operators()
    machines_df = load_machines()
    weather_df = load_weather()
    tasks_df = load_tasks()
    telemetry_df = load_telemetry()

    features_df, _, _ = build_eta_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)
    demo_row = features_df[features_df["task_id"] == config.DEMO_TASK_ID]
    if len(demo_row) == 0:
        print(f"Demo task {config.DEMO_TASK_ID} not found in the feature dataset — cannot run the demo.")
        return
    task_features = demo_row.iloc[0]

    bundle = load_eta_model()

    # --- 1. Baseline ETA -----------------------------------------------
    baseline_eta = predict_eta(task_features, bundle)
    print(f"\n1) Baseline ETA (model: {bundle.model_name}): {baseline_eta:.1f} min")
    print(f"   Naive planner estimate (estimated_time_min): {task_features['estimated_time_min']:.1f} min")
    print(f"   Actual recorded outcome (actual_time_min):    {task_features['actual_time_min']:.1f} min")

    # --- 2. Operator Twin -------------------------------------------------
    twin = get_operator_profile(config.DEMO_OPERATOR_ID, tasks_df, telemetry_df, operators_df)
    print(f"\n2) Operator Twin for {config.DEMO_OPERATOR_ID} (n_tasks={twin['nTasks']}):")
    for k, v in twin.items():
        if k not in ("operatorId", "nTasks"):
            print(f"   {k:<22} {v}")

    # --- 3. Personalized ETA (pre-task) -----------------------------------
    personalized = predict_personalized_eta(task_features, twin, telemetry_so_far=None, model_bundle=bundle)
    print(f"\n3) Personalized ETA range (pre-task):")
    print(f"   eta_min={personalized['eta_min']}  eta_max={personalized['eta_max']}  point={personalized['eta_point']}")
    print(f"   original_eta (naive planner): {personalized['original_eta']}")
    print(f"   reason: {personalized['reason']}")
    print(f"   buckets_remaining: {personalized['buckets_remaining']}")

    # --- 4. Remaining work + Dynamic ETA (task in progress) ---------------
    task_telemetry = telemetry_df[telemetry_df["task_id"] == config.DEMO_TASK_ID].sort_values("timestamp")
    halfway = max(1, len(task_telemetry) // 2)
    telemetry_so_far = task_telemetry.iloc[:halfway]

    remaining = calculate_remaining_work(task_features, telemetry_so_far)
    print(f"\n4) Remaining work (after {len(telemetry_so_far)}/{len(task_telemetry)} telemetry readings):")
    for k, v in remaining.items():
        print(f"   {k:<20} {v}")

    dynamic = predict_dynamic_eta(
        task_features, telemetry_so_far, twin, original_point_eta_min=baseline_eta, model_bundle=bundle
    )
    print(f"\n   Dynamic ETA update:")
    print(f"   eta_min={dynamic['eta_min']}  eta_max={dynamic['eta_max']}  point={dynamic['eta_point']}")
    print(f"   original_eta: {dynamic['original_eta']}")
    print(f"   cycle_time_change_pct: {dynamic['cycle_time_change_pct']}")
    print(f"   reason: {dynamic['reason']}")

    print(f"\n5) Main ETA drivers (factors):")
    for f in personalized["factors"]:
        print(f"   {f['name']:<20} impact={f['impact']:<9} ({f['detail']})")

    print("\nDemo inference completed with no errors.\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--train", action="store_true", help="Force-retrain the ETA model.")
    parser.add_argument("--demo-only", action="store_true", help="Skip training; just run inference.")
    args = parser.parse_args()

    if not args.demo_only and (args.train or not eta_model_exists()):
        print("Training ETA model...\n")
        report = train_and_select(save=True)
        print_report(report)
    else:
        print("Using existing saved ETA model (pass --train to retrain).")

    run_demo()


if __name__ == "__main__":
    main()
