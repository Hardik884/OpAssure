"""Remaining-work calculation from a task's own telemetry so far.

Deliberately does NOT estimate trucks remaining: the synthetic data has no
bucket-per-truck capacity field, and inventing a conversion ratio would be
exactly the kind of fabricated number the project rules forbid. `trucks_remaining`
stays `None` until the data model actually carries truck capacity.
"""

import pandas as pd


def calculate_remaining_work(task_row: pd.Series, telemetry_so_far: pd.DataFrame | None = None) -> dict:
    """Return buckets completed/remaining for a task, given whatever
    telemetry has been recorded for it so far.

    `telemetry_so_far` may be empty or None (task not started yet) — in that
    case the task's full `estimated_buckets` is reported as remaining.
    """
    total_buckets = int(task_row["estimated_buckets"])

    if telemetry_so_far is None or len(telemetry_so_far) == 0:
        buckets_completed = 0
    else:
        buckets_completed = int(telemetry_so_far["load_cycles"].sum())

    buckets_remaining = max(0, total_buckets - buckets_completed)
    pct_complete = round(min(1.0, buckets_completed / total_buckets), 3) if total_buckets > 0 else 0.0

    return {
        "total_buckets": total_buckets,
        "buckets_completed": buckets_completed,
        "buckets_remaining": buckets_remaining,
        "pct_complete": pct_complete,
        # Not defensible from the current data model — see module docstring.
        "trucks_remaining": None,
    }
