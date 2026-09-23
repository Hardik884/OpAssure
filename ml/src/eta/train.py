"""Train, compare, and save the baseline ETA model.

Trains at least two candidate models on the **train** split, scores them on
the **val** split (that's what "best" is chosen by), and reports a final,
untouched **test**-split score for the winner. The time-aware split from
`src.evaluation.splits` is reused as-is — never a random shuffle.

Run directly:

    python -m src.eta.train        (from ml/, with the venv active)

or via `python run_eta_pipeline.py` at the repo root, which also runs
evaluation + a demo inference afterward.
"""

import json
from datetime import datetime, timezone

import joblib
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression

from src.common import config
from src.common.loaders import load_machines, load_operators, load_tasks, load_telemetry, load_weather
from src.eta.dataset import build_eta_dataset
from src.evaluation.metrics import regression_metrics
from src.evaluation.splits import time_aware_split

# Kept as module-level aliases for backward compatibility (existing callers/
# tests import MODEL_PATH/METADATA_PATH from here) — config.py is now the
# single source of truth for these paths, so model_io.py (pure inference)
# doesn't have to import this training module just to find them.
MODEL_PATH = config.ETA_MODEL_PATH
METADATA_PATH = config.ETA_METADATA_PATH


def get_candidate_models() -> dict[str, object]:
    """At least two reasonable, cheap-to-train baselines: a linear model
    (interpretable, fast, a fair "can we beat a straight line" bar) and a
    random forest (captures the non-linear weather/fatigue/degradation
    interactions the generator plants, without needing much tuning)."""
    return {
        "linear_regression": LinearRegression(),
        "random_forest": RandomForestRegressor(
            n_estimators=200,
            max_depth=8,
            min_samples_leaf=3,
            random_state=config.SEED,
            n_jobs=-1,
        ),
    }


def train_and_select(save: bool = True) -> dict:
    """Build the dataset, train + compare candidates, select the best by
    validation MAE, compute residual-quantile interval offsets, and (by
    default) save the winning model + metadata to `ml/models/eta/`.

    Returns the full report dict (also written as metadata.json when saving).
    """
    operators_df = load_operators()
    machines_df = load_machines()
    weather_df = load_weather()
    tasks_df = load_tasks()
    telemetry_df = load_telemetry()

    features_df, target, feature_cols = build_eta_dataset(
        tasks_df, operators_df, machines_df, weather_df, telemetry_df
    )

    train_df, val_df, test_df = time_aware_split(features_df)
    y_train = train_df["actual_time_min"]
    y_val = val_df["actual_time_min"]
    y_test = test_df["actual_time_min"]

    X_train = train_df[feature_cols]
    X_val = val_df[feature_cols]
    X_test = test_df[feature_cols]

    candidates_report = {}
    fitted_models = {}
    for name, model in get_candidate_models().items():
        model.fit(X_train, y_train)
        val_pred = model.predict(X_val)
        candidates_report[name] = {"val": regression_metrics(y_val, val_pred)}
        fitted_models[name] = model

    best_name = min(candidates_report, key=lambda n: candidates_report[n]["val"]["mae"])
    best_model = fitted_models[best_name]

    # Final, untouched holdout evaluation for the winner only.
    test_pred = best_model.predict(X_test)
    candidates_report[best_name]["test"] = regression_metrics(y_test, test_pred)

    # Residual-quantile prediction interval, computed on the validation set
    # (never on test — test stays an honest, unused-for-any-decision holdout).
    val_pred_best = best_model.predict(X_val)
    residuals = (y_val.values - val_pred_best)
    q_low, q_high = config.ETA_RESIDUAL_QUANTILES
    quantile_offsets = {
        "q_low": float(pd.Series(residuals).quantile(q_low)),
        "q_high": float(pd.Series(residuals).quantile(q_high)),
    }

    report = {
        "trained_at": datetime.now(timezone.utc).isoformat(),
        "seed": config.SEED,
        "feature_columns": feature_cols,
        "target_column": "actual_time_min",
        "split_sizes": {"train": len(train_df), "val": len(val_df), "test": len(test_df)},
        "candidates": candidates_report,
        "selected_model": best_name,
        "residual_quantiles": {"levels": list(config.ETA_RESIDUAL_QUANTILES), "offsets": quantile_offsets},
        # Not JSON-serialized (stripped out before writing metadata.json below) —
        # kept in the in-memory report so callers like the test suite can build
        # an EtaModelBundle without round-tripping through disk.
        "_fitted_model": best_model,
    }

    if save:
        config.ETA_MODEL_DIR.mkdir(parents=True, exist_ok=True)
        joblib.dump(best_model, MODEL_PATH)
        metadata_only = {k: v for k, v in report.items() if not k.startswith("_")}
        METADATA_PATH.write_text(json.dumps(metadata_only, indent=2))

    return report


def main() -> None:
    report = train_and_select(save=True)
    print("ETA model training complete.\n")
    print(f"Split sizes: {report['split_sizes']}")
    print("\nCandidate comparison (validation set):")
    for name, scores in report["candidates"].items():
        v = scores["val"]
        marker = "  <- selected" if name == report["selected_model"] else ""
        print(f"  {name:<18} MAE={v['mae']:6.2f}  RMSE={v['rmse']:6.2f}  median_AE={v['median_ae']:6.2f}{marker}")

    best = report["candidates"][report["selected_model"]]
    print(f"\nSelected model: {report['selected_model']}")
    print(f"Held-out test performance (never used for model selection):")
    t = best["test"]
    print(f"  MAE={t['mae']:.2f} min   RMSE={t['rmse']:.2f} min   median_AE={t['median_ae']:.2f} min")

    q = report["residual_quantiles"]["offsets"]
    print(f"\nResidual-quantile interval offsets (from validation set): [{q['q_low']:+.1f}, {q['q_high']:+.1f}] min")
    print(f"\nSaved model  -> {MODEL_PATH}")
    print(f"Saved metadata -> {METADATA_PATH}")


if __name__ == "__main__":
    main()
