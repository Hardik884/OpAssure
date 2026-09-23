"""Operator-level features.

These are the operator's static profile fields, turned into ML-ready columns.
Historical (behavioral) operator features that change over time live in
`telemetry_features.py`, since they depend on the as-of cutoff.
"""

import pandas as pd

SKILL_ORDER = {"novice": 0, "intermediate": 1, "expert": 2}


def build_operator_features(operators_df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per operator with ML-ready static features."""
    df = operators_df.copy()
    df["skill_level"] = df["skill"].map(SKILL_ORDER)
    return df[
        [
            "operator_id",
            "skill",
            "skill_level",
            "base_speed",
            "fatigue_start_hour",
            "heat_sensitivity",
            "rain_sensitivity",
            "belt_skip_probability_when_idle",
        ]
    ]
