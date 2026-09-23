"""Task-level static features — what's known about a task at planning time.

Deliberately excludes anything only known *after* the task runs
(`actual_time_min`, telemetry aggregates for this task) — those are targets
or leakage, not inputs. See `build_features.py` for how targets are attached.
"""

import pandas as pd

from src.common.time_utils import add_time_parts

TASK_TYPE_DUMMIES = ["excavation", "loading", "grading", "trenching", "hauling"]
ZONE_DUMMIES = ["zone_a", "zone_b", "zone_c", "zone_d"]


def build_task_features(tasks_df: pd.DataFrame) -> pd.DataFrame:
    df = add_time_parts(tasks_df, "start_time")
    for t in TASK_TYPE_DUMMIES:
        df[f"task_type_{t}"] = (df["task_type"] == t).astype(int)
    for z in ZONE_DUMMIES:
        df[f"zone_{z}"] = (df["zone"] == z).astype(int)
    df["is_truck_dependent_type"] = df["task_type"].isin(["loading", "hauling"]).astype(int)
    return df
