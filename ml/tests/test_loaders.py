"""Tests for data loading utilities.

Writes the in-memory `tables` fixture to a temp directory so loaders are
exercised against real files (read_csv, dtype handling) without depending on
`data/synthetic/` already being populated on disk.
"""

from pathlib import Path

from src.common.loaders import load_table
from src.common.io import write_csv


def test_load_table_round_trips_every_table(tables, tmp_path: Path):
    for name, df in tables.items():
        path = write_csv(df, tmp_path / f"{name}.csv")
        loaded = load_table_from_path(name, path)
        assert len(loaded) == len(df)
        assert list(loaded.columns) == list(df.columns)


def load_table_from_path(name: str, path: Path):
    from src.common.loaders import TABLE_LOADERS

    loader = TABLE_LOADERS[name]
    return loader(path=path)


def test_operator_ids_stay_strings(tables, tmp_path: Path):
    path = write_csv(tables["operators"], tmp_path / "operators.csv")
    loaded = load_table_from_path("operators", path)
    assert loaded["operator_id"].dtype == object
    assert (loaded["operator_id"].str.startswith("OP")).all()


def test_unknown_table_raises():
    import pytest

    with pytest.raises(ValueError):
        load_table("not_a_real_table")
