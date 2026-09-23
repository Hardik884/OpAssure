"""Small, boring CSV read/write helpers used throughout the ML package.

Kept deliberately thin — pandas already does the real work. These wrappers
exist so every module writes files the same way (parent dirs created,
consistent float formatting) instead of each caller reimplementing it.
"""

from pathlib import Path

import pandas as pd


def write_csv(df: pd.DataFrame, path: Path) -> Path:
    """Write ``df`` to ``path`` as CSV, creating parent directories if needed."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def read_csv(path: Path, parse_dates: list[str] | None = None) -> pd.DataFrame:
    """Read a CSV, raising a clear error if it doesn't exist yet."""
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Expected data file not found: {path}\n"
            "Run the synthetic data generator first: "
            "`python ml/run_pipeline.py --regenerate`"
        )
    return pd.read_csv(path, parse_dates=parse_dates)
