"""Data loading utilities for every raw/synthetic table OpAssure's ML layer uses.

Each loader returns a pandas DataFrame with timestamp columns parsed and ID
columns kept as strings (never inferred as ints — `OP1001` must stay `OP1001`,
and leading zeros in machine/task IDs must never be dropped).

All loaders read from `data/synthetic/` (or `data/ground_truth/` for labels) by
default. Pass an explicit `path` to point at a different file (e.g. a real
dataset once the backend produces one, or a fixture in tests).
"""

from pathlib import Path

import pandas as pd

from src.common import config
from src.common.io import read_csv

_ID_DTYPES = {
    "operator_id": str,
    "machine_id": str,
    "task_id": str,
    "worker_id": str,
    "incident_id": str,
    "near_miss_id": str,
    "label_id": str,
    "event_id": str,
}


def _read_table(filename: str, base_dir: Path, parse_dates: list[str] | None, path: Path | None) -> pd.DataFrame:
    target = Path(path) if path is not None else base_dir / filename
    df = read_csv(target, parse_dates=parse_dates)
    for col, dtype in _ID_DTYPES.items():
        if col in df.columns:
            df[col] = df[col].astype(dtype)
    return df


def load_operators(path: Path | None = None) -> pd.DataFrame:
    return _read_table("operators.csv", config.SYNTHETIC_DIR, None, path)


def load_machines(path: Path | None = None) -> pd.DataFrame:
    return _read_table("machines.csv", config.SYNTHETIC_DIR, None, path)


def load_weather(path: Path | None = None) -> pd.DataFrame:
    return _read_table("weather.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_tasks(path: Path | None = None) -> pd.DataFrame:
    return _read_table("tasks.csv", config.SYNTHETIC_DIR, ["start_time"], path)


def load_telemetry(path: Path | None = None) -> pd.DataFrame:
    return _read_table("telemetry.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_worker_positions(path: Path | None = None) -> pd.DataFrame:
    return _read_table("worker_positions.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_incidents(path: Path | None = None) -> pd.DataFrame:
    return _read_table("incidents.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_near_misses(path: Path | None = None) -> pd.DataFrame:
    return _read_table("near_misses.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_training_events(path: Path | None = None) -> pd.DataFrame:
    return _read_table("training_events.csv", config.SYNTHETIC_DIR, ["timestamp"], path)


def load_ground_truth_labels(path: Path | None = None) -> pd.DataFrame:
    return _read_table("ground_truth_labels.csv", config.GROUND_TRUTH_DIR, ["start_date", "end_date"], path)


def load_task_ground_truth(path: Path | None = None) -> pd.DataFrame:
    """Per-task boolean labels for the planted patterns (finer-grained than
    `ground_truth_labels`, used by `/ml-evaluation` and `/data-validation`)."""
    return _read_table("task_ground_truth.csv", config.GROUND_TRUTH_DIR, None, path)


TABLE_LOADERS = {
    "operators": load_operators,
    "machines": load_machines,
    "weather": load_weather,
    "tasks": load_tasks,
    "telemetry": load_telemetry,
    "worker_positions": load_worker_positions,
    "incidents": load_incidents,
    "near_misses": load_near_misses,
    "training_events": load_training_events,
    "ground_truth_labels": load_ground_truth_labels,
    "task_ground_truth": load_task_ground_truth,
}


def load_table(name: str) -> pd.DataFrame:
    """Load any known table by name, e.g. `load_table("telemetry")`."""
    if name not in TABLE_LOADERS:
        raise ValueError(f"Unknown table '{name}'. Known tables: {sorted(TABLE_LOADERS)}")
    return TABLE_LOADERS[name]()


def load_all() -> dict[str, pd.DataFrame]:
    """Load every table into a dict keyed by table name."""
    return {name: loader() for name, loader in TABLE_LOADERS.items()}
