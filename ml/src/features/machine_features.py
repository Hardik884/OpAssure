"""Machine-level features.

Static machine attributes only. Machine *condition trend* (the signal that
reveals degradation) is time-dependent and computed in
`telemetry_features.py` from historical telemetry only — never from static
`health_drift`, since a real deployment won't have that ground-truth value.
"""

import pandas as pd

TYPE_DUMMIES = ["excavator", "dozer", "loader"]


def build_machine_features(machines_df: pd.DataFrame) -> pd.DataFrame:
    """Return one row per machine with ML-ready static features."""
    df = machines_df.copy()
    for t in TYPE_DUMMIES:
        df[f"machine_type_{t}"] = (df["type"] == t).astype(int)
    cols = ["machine_id", "type", "age_years"] + [f"machine_type_{t}" for t in TYPE_DUMMIES]
    return df[cols]
