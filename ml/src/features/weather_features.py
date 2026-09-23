"""Weather features and the as-of merge used to attach weather to an event."""

import pandas as pd

CONDITION_DUMMIES = ["clear", "cloudy", "rain", "storm"]


def build_weather_features(weather_df: pd.DataFrame) -> pd.DataFrame:
    """Clean/encode the raw weather table (condition one-hot, kept tidy)."""
    df = weather_df.copy()
    for c in CONDITION_DUMMIES:
        df[f"weather_{c}"] = (df["condition"] == c).astype(int)
    df["is_wet"] = df["condition"].isin(["rain", "storm"]).astype(int)
    return df
