"""Load the trained ETA model artifact without retraining it.

`train.py` is the only thing that fits a model. Everything else — the demo
script, tests, and eventually the backend — loads the saved artifact through
`load_eta_model()`, which caches it in-process so repeated calls in the same
run don't hit disk again.
"""

import json
from dataclasses import dataclass

import joblib

from src.common import config
from src.eta.train import METADATA_PATH, MODEL_PATH


@dataclass(frozen=True)
class EtaModelBundle:
    model: object
    feature_columns: list[str]
    model_name: str
    metrics: dict
    residual_quantile_offsets: dict[str, float]


_CACHE: EtaModelBundle | None = None


def eta_model_exists() -> bool:
    return MODEL_PATH.exists() and METADATA_PATH.exists()


def load_eta_model(force_reload: bool = False) -> EtaModelBundle:
    """Load the saved model + its metadata. Raises a clear error if training
    hasn't been run yet, instead of silently training on the fly."""
    global _CACHE
    if _CACHE is not None and not force_reload:
        return _CACHE

    if not eta_model_exists():
        raise FileNotFoundError(
            f"No trained ETA model found at {MODEL_PATH}.\n"
            "Train it first: `python -m src.eta.train` (from ml/, with the venv active) "
            "or `python run_eta_pipeline.py --train`."
        )

    model = joblib.load(MODEL_PATH)
    metadata = json.loads(METADATA_PATH.read_text())

    selected = metadata["selected_model"]
    _CACHE = EtaModelBundle(
        model=model,
        feature_columns=metadata["feature_columns"],
        model_name=selected,
        metrics=metadata["candidates"][selected],
        residual_quantile_offsets=metadata["residual_quantiles"]["offsets"],
    )
    return _CACHE
