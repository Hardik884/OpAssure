"""Time-aware historical aggregates from telemetry/tasks.

This is the module that makes the pipeline "time-aware": for each task, the
operator- and machine-history features are computed using an **expanding
window of only the tasks that started strictly before this task**. A task
never sees its own outcome, or any future task's outcome, in its input
features. This is what prevents the classic leakage bug of "average actual
time" secretly including the row you're trying to predict.

These functions are shared verbatim by ETA, Operator Twin, and anomaly
detection (`CLAUDE.md` §11 / requirement: "reusable feature functions").
"""

import numpy as np
import pandas as pd


def _expanding_prior_mean(group: pd.DataFrame, col: str) -> pd.Series:
    """Expanding mean of `col` using only *prior* rows (shifted by one)."""
    return group[col].shift(1).expanding().mean()


def add_operator_history_features(tasks_df: pd.DataFrame) -> pd.DataFrame:
    """Add each operator's historical performance, known only up to (not
    including) the current task's start_time."""
    df = tasks_df.sort_values(["operator_id", "start_time"]).copy()

    # NOTE: deliberately NOT calling `.reset_index(drop=True)` on the apply()
    # results below. `df` still carries the original (non-sequential) row
    # labels from `tasks_df` after `sort_values`, and `grouped.apply(...,
    # group_keys=False)` returns a Series whose index labels are those same
    # original labels (just reordered to match df's current row order).
    # Assigning `df[col] = series` aligns by label, so keeping those labels
    # intact is what makes the assignment land on the correct rows;
    # resetting to a fresh 0..n-1 index before assigning silently
    # reshuffles values onto the wrong rows.
    grouped = df.groupby("operator_id", group_keys=False)
    df["operator_avg_actual_time_min_prior"] = grouped.apply(
        lambda g: _expanding_prior_mean(g, "actual_time_min"), include_groups=False
    )
    df["operator_avg_estimate_error_prior"] = grouped.apply(
        lambda g: _expanding_prior_mean(g.assign(_err=g["actual_time_min"] - g["estimated_time_min"]), "_err"),
        include_groups=False,
    )
    df["operator_tasks_completed_prior"] = grouped.cumcount()

    # No history yet (operator's first task) -> fall back to the planner estimate,
    # i.e. "assume average" rather than leaving NaN (NaN would break most models).
    df["operator_avg_actual_time_min_prior"] = df["operator_avg_actual_time_min_prior"].fillna(
        df["estimated_time_min"]
    )
    df["operator_avg_estimate_error_prior"] = df["operator_avg_estimate_error_prior"].fillna(0.0)

    return df.sort_index()


def add_machine_history_features(tasks_df: pd.DataFrame) -> pd.DataFrame:
    """Add each machine's recent performance trend, using only tasks that
    started strictly before the current one. A rising trend here is exactly
    the signal that should let a model catch machine degradation without
    ever being told which machine was planted as degrading."""
    df = tasks_df.sort_values(["machine_id", "start_time"]).copy()

    # See the note in add_operator_history_features(): no `.reset_index(drop=True)`
    # here either, for the same label-alignment reason.
    grouped = df.groupby("machine_id", group_keys=False)
    df["machine_avg_actual_time_min_prior"] = grouped.apply(
        lambda g: _expanding_prior_mean(g, "actual_time_min"), include_groups=False
    )

    # Rolling-recent (last 5 prior tasks) vs all-time prior average: a gap
    # between them is a cheap, honest "is this machine trending worse lately" signal.
    def _recent_vs_alltime(g: pd.DataFrame) -> pd.Series:
        prior = g["actual_time_min"].shift(1)
        recent = prior.rolling(5, min_periods=1).mean()
        alltime = prior.expanding().mean()
        return recent - alltime

    df["machine_recent_vs_alltime_gap_prior"] = grouped.apply(_recent_vs_alltime, include_groups=False)
    df["machine_tasks_completed_prior"] = grouped.cumcount()

    df["machine_avg_actual_time_min_prior"] = df["machine_avg_actual_time_min_prior"].fillna(
        df["estimated_time_min"]
    )
    df["machine_recent_vs_alltime_gap_prior"] = df["machine_recent_vs_alltime_gap_prior"].fillna(0.0)

    return df.sort_index()


def add_operator_fuel_efficiency_features(tasks_df: pd.DataFrame, telemetry_df: pd.DataFrame) -> pd.DataFrame:
    """Add each operator's historical fuel-per-active-minute, computed only
    from telemetry belonging to tasks that started before the current task.
    Used by anomaly detection to flag persistently high fuel use."""
    df = tasks_df.sort_values(["operator_id", "start_time"]).copy()

    task_fuel = (
        telemetry_df.groupby("task_id")
        .agg(fuel_used_l=("fuel_used_l", "sum"), moving_minutes=("machine_moving", "sum"))
        .reset_index()
    )
    task_fuel["moving_minutes"] = task_fuel["moving_minutes"].replace(0, np.nan)
    task_fuel["fuel_per_moving_min"] = task_fuel["fuel_used_l"] / task_fuel["moving_minutes"]

    df = df.merge(task_fuel[["task_id", "fuel_per_moving_min"]], on="task_id", how="left")
    df["fuel_per_moving_min"] = df["fuel_per_moving_min"].fillna(df["fuel_per_moving_min"].median())

    # `df` got a fresh sequential index from the merge() above (in the same
    # row order), so this one happens to line up either way — kept
    # reset-free for consistency with the other functions in this file.
    grouped = df.groupby("operator_id", group_keys=False)
    df["operator_avg_fuel_per_moving_min_prior"] = grouped.apply(
        lambda g: _expanding_prior_mean(g, "fuel_per_moving_min"), include_groups=False
    )
    df["operator_avg_fuel_per_moving_min_prior"] = df["operator_avg_fuel_per_moving_min_prior"].fillna(
        df["fuel_per_moving_min"]
    )

    return df.sort_index()
