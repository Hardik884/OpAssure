"""Regression evaluation metrics shared by model training and `/ml-evaluation`."""

import numpy as np
from sklearn.metrics import mean_absolute_error, mean_squared_error, median_absolute_error


def regression_metrics(y_true, y_pred) -> dict[str, float]:
    """MAE, RMSE, and median absolute error — the three metrics required for
    comparing ETA model candidates."""
    y_true = np.asarray(y_true, dtype=float)
    y_pred = np.asarray(y_pred, dtype=float)
    return {
        "mae": float(mean_absolute_error(y_true, y_pred)),
        "rmse": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "median_ae": float(median_absolute_error(y_true, y_pred)),
    }
