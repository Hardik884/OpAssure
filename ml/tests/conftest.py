"""Shared pytest fixtures: generate the synthetic dataset once per test session."""

import pytest

from src.common.synthetic import generate_all
from src.eta.model_io import EtaModelBundle
from src.eta.train import train_and_select


@pytest.fixture(scope="session")
def tables():
    """In-memory generated tables (does not touch disk)."""
    return generate_all()


@pytest.fixture(scope="session")
def eta_report():
    """Train the ETA model once per test session, in memory only
    (`save=False`) so tests never overwrite the real saved artifact under
    `ml/models/eta/`."""
    return train_and_select(save=False)


@pytest.fixture(scope="session")
def eta_bundle(eta_report):
    """An EtaModelBundle built from the in-memory `eta_report`, so tests can
    call the inference functions without touching disk."""
    selected = eta_report["selected_model"]
    return EtaModelBundle(
        model=eta_report["_fitted_model"],
        feature_columns=eta_report["feature_columns"],
        model_name=selected,
        metrics=eta_report["candidates"][selected],
        residual_quantile_offsets=eta_report["residual_quantiles"]["offsets"],
    )
