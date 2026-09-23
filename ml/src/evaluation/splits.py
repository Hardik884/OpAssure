"""Time-aware train/validation/test splitting.

Splits are chronological, never shuffled: train is the earliest slice, test
is the most recent slice. This mirrors how the model will actually be used
(predict tasks that haven't happened yet) and avoids leaking future
information into training, per the project's engineering rules.
"""

import pandas as pd

from src.common import config


def time_aware_split(
    df: pd.DataFrame,
    time_col: str = "start_time",
    train_frac: float = config.TRAIN_FRAC,
    val_frac: float = config.VAL_FRAC,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Split `df` into (train, val, test) ordered strictly by `time_col`.

    No row in `train` starts after any row in `val`; no row in `val` starts
    after any row in `test`. Ties at the split boundary stay together on the
    earlier side so no timestamp is duplicated across splits.
    """
    if not 0 < train_frac < 1 or not 0 <= val_frac < 1 or train_frac + val_frac >= 1:
        raise ValueError("train_frac + val_frac must be < 1, and both must be valid fractions")

    ordered = df.sort_values(time_col).reset_index(drop=True)
    n = len(ordered)
    train_end = int(n * train_frac)
    val_end = train_end + int(n * val_frac)

    train_df = ordered.iloc[:train_end]
    val_df = ordered.iloc[train_end:val_end]
    test_df = ordered.iloc[val_end:]

    return train_df, val_df, test_df
