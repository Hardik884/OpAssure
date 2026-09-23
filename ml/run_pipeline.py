#!/usr/bin/env python
"""OpAssure ML foundation — single entry point.

Usage (from the repo root or from `ml/`):

    python ml/run_pipeline.py                 # generate data only if missing, then build features
    python ml/run_pipeline.py --regenerate     # force-regenerate synthetic data first

What it does:
  1. Generates the synthetic dataset into data/synthetic/ + data/ground_truth/
     (unless it already exists and --regenerate wasn't passed).
  2. Loads every table.
  3. Builds the shared task-level feature dataset.
  4. Saves it to data/processed/task_features.csv.
  5. Prints a summary report.

No models are trained here — this script only builds the ML-ready dataset.
"""

import argparse
import sys
from pathlib import Path

# Make `src` importable whether this script is run from the repo root or from ml/.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.common import config  # noqa: E402
from src.common.io import write_csv  # noqa: E402
from src.common.loaders import (  # noqa: E402
    load_machines,
    load_operators,
    load_task_ground_truth,
    load_tasks,
    load_telemetry,
    load_weather,
)
from src.common.synthetic import generate_all, write_all  # noqa: E402
from src.eta.dataset import build_eta_dataset  # noqa: E402
from src.evaluation.splits import time_aware_split  # noqa: E402


def synthetic_data_exists() -> bool:
    required = ["operators.csv", "machines.csv", "weather.csv", "tasks.csv", "telemetry.csv"]
    return all((config.SYNTHETIC_DIR / f).exists() for f in required)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--regenerate", action="store_true", help="Force-regenerate synthetic data even if it already exists."
    )
    args = parser.parse_args()

    if args.regenerate or not synthetic_data_exists():
        print("Generating synthetic dataset...")
        tables = generate_all()
        written = write_all(tables)
        for name, df in tables.items():
            print(f"  {name:<20} {len(df):>7} rows  -> {written[name]}")
    else:
        print("Synthetic dataset already present in data/synthetic/ (use --regenerate to rebuild).")

    print("\nLoading tables...")
    operators_df = load_operators()
    machines_df = load_machines()
    weather_df = load_weather()
    tasks_df = load_tasks()
    telemetry_df = load_telemetry()
    task_ground_truth_df = load_task_ground_truth()

    print("Building shared task-level feature dataset...")
    features_df, target, cols = build_eta_dataset(tasks_df, operators_df, machines_df, weather_df, telemetry_df)

    out_path = write_csv(features_df, config.PROCESSED_DIR / "task_features.csv")

    train_df, val_df, test_df = time_aware_split(features_df)

    print("\n=== ML Foundation Pipeline: Summary ===")
    print(f"Operators:            {len(operators_df)}")
    print(f"Machines:             {len(machines_df)}")
    print(f"Weather readings:     {len(weather_df)}")
    print(f"Tasks:                {len(tasks_df)}")
    print(f"Telemetry rows:       {len(telemetry_df)}")
    print(f"Task ground truth:    {len(task_ground_truth_df)} rows, columns: {list(task_ground_truth_df.columns[1:])}")
    print(f"\nFeature matrix:       {features_df.shape[0]} rows x {features_df.shape[1]} columns")
    print(f"Usable feature cols:  {len(cols)}")
    print(f"Target column:        actual_time_min (min={target.min():.1f}, max={target.max():.1f}, mean={target.mean():.1f})")
    print(f"\nTime-aware split:     train={len(train_df)}  val={len(val_df)}  test={len(test_df)}")
    print(
        f"Split boundaries ok:  "
        f"{train_df['start_time'].max() <= val_df['start_time'].min() if len(val_df) else True} "
        f"and "
        f"{val_df['start_time'].max() <= test_df['start_time'].min() if len(val_df) and len(test_df) else True}"
    )
    print(f"\nProcessed dataset saved to: {out_path}")
    print("\nDemo scenario check:")
    demo_task = features_df[features_df["task_id"] == config.DEMO_TASK_ID]
    print(
        f"  {config.DEMO_TASK_ID} / {config.DEMO_OPERATOR_ID} / {config.DEMO_MACHINE_ID}: "
        f"{'FOUND' if len(demo_task) else 'MISSING'}"
    )
    print("\nPipeline completed with no errors.")


if __name__ == "__main__":
    main()
