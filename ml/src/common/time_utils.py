"""Timestamp helpers shared by the feature pipeline.

Centralizing these keeps "what counts as afternoon", "how do we merge weather
onto an event", etc. defined once instead of duplicated per feature module.
"""

import pandas as pd


def add_time_parts(df: pd.DataFrame, time_col: str) -> pd.DataFrame:
    """Add hour_of_day / day_of_week / is_weekend columns derived from ``time_col``."""
    df = df.copy()
    ts = pd.to_datetime(df[time_col])
    df["hour_of_day"] = ts.dt.hour + ts.dt.minute / 60.0
    df["day_of_week"] = ts.dt.dayofweek
    df["is_weekend"] = df["day_of_week"].isin([5, 6])
    return df


def merge_asof_weather(
    df: pd.DataFrame,
    weather_df: pd.DataFrame,
    time_col: str,
    weather_time_col: str = "timestamp",
) -> pd.DataFrame:
    """Attach the most recent weather reading at or before each row's timestamp.

    Uses a backward as-of join so no row ever sees a *future* weather reading —
    this is what keeps weather features honest for time-aware modeling.
    """
    left = df.copy()
    left["_sort_ts"] = pd.to_datetime(left[time_col])
    right = weather_df.copy()
    right["_sort_ts"] = pd.to_datetime(right[weather_time_col])
    right = right.sort_values("_sort_ts")

    merged = pd.merge_asof(
        left.sort_values("_sort_ts"),
        right.drop(columns=[weather_time_col]),
        on="_sort_ts",
        direction="backward",
    )
    return merged.drop(columns=["_sort_ts"]).sort_index()
