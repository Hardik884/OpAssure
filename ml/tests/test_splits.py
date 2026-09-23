"""Tests for time-aware splitting: chronological order, no shuffling, no overlap."""

import pytest

from src.eta.dataset import build_eta_dataset
from src.evaluation.splits import time_aware_split


def test_split_is_chronological_and_non_overlapping(tables):
    df, _, _ = build_eta_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )
    train, val, test = time_aware_split(df, train_frac=0.7, val_frac=0.15)

    assert len(train) + len(val) + len(test) == len(df)
    assert train["start_time"].max() <= val["start_time"].min()
    assert val["start_time"].max() <= test["start_time"].min()


def test_split_fractions_roughly_respected(tables):
    df, _, _ = build_eta_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )
    train, val, test = time_aware_split(df, train_frac=0.7, val_frac=0.15)
    n = len(df)
    assert abs(len(train) / n - 0.7) < 0.02
    assert abs(len(val) / n - 0.15) < 0.02


def test_invalid_fractions_raise():
    import pandas as pd

    df = pd.DataFrame({"start_time": pd.date_range("2026-01-01", periods=10)})
    with pytest.raises(ValueError):
        time_aware_split(df, train_frac=0.9, val_frac=0.2)
