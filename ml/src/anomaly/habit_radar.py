"""Habit Radar: detects REPEATED behavioural patterns from telemetry, not
single events.

Primary planted scenario (see `CLAUDE.md` §6, "seatbelt habit"):

    truck wait -> seatbelt removed -> long idle -> truck arrives ->
    machine starts moving -> seatbelt still unfastened

Each task's telemetry contains at most one contiguous idle block (see the
generator), so a task-level "idle -> moving" transition is exactly one
*opportunity* for this habit to occur. We don't need general-purpose
sequence mining (PrefixSpan etc.) to find a single fixed-length pattern
reliably — a deterministic per-task scan is simpler, exactly as accurate,
and easy to audit. This intentionally does NOT flag anything as a "habit"
from a single occurrence: `HABIT_MIN_OPPORTUNITIES` and `HABIT_MIN_COUNT`
(config.py) both have to be met.
"""

import pandas as pd

from src.common import config

HABIT_TYPE_SEATBELT_TRUCK_WAIT = "seatbelt_during_truck_wait"


def _task_opportunities(telemetry_df: pd.DataFrame) -> pd.DataFrame:
    """One row per task with a truck-wait idle block followed by a
    within-task resumption of movement: was the seatbelt off during that
    idle, and is it still off the moment movement resumes?

    Tasks with no idle->moving transition in their own telemetry (e.g. the
    idle block runs to the very end of the recorded interval) simply don't
    produce a row here — not a bug, just no opportunity observed within
    that task's telemetry.

    Vectorized (via `groupby(...).shift(1)`) rather than a per-task Python
    loop — the original loop-per-task version took ~2 seconds on the full
    synthetic dataset (~2800 tasks), which is a real cost since this
    function is on `generate_operator_state()`'s path and can also run
    inside `update_operator_state()`'s realtime path when a transition
    occurs. Same semantics, same output columns — see `test_habit_radar.py`
    for the equivalence check against the original per-task logic.
    """
    columns = ["task_id", "operator_id", "unbuckled_during_idle", "unbuckled_at_resume"]
    if len(telemetry_df) == 0:
        return pd.DataFrame(columns=columns)

    df = telemetry_df.sort_values(["task_id", "timestamp"])
    grouped = df.groupby("task_id", sort=False)
    prev_moving = grouped["machine_moving"].shift(1)
    prev_idle_reason = grouped["idle_reason"].shift(1)
    prev_seatbelt = grouped["seatbelt_status"].shift(1)

    is_transition = df["machine_moving"] & (prev_moving == False) & (prev_idle_reason == "waiting_for_truck")  # noqa: E712

    out = df.loc[is_transition, ["task_id", "operator_id"]].copy()
    out["unbuckled_during_idle"] = (prev_seatbelt[is_transition] == "unbuckled").values
    out["unbuckled_at_resume"] = (df.loc[is_transition, "seatbelt_status"] == "unbuckled").values
    return out.reset_index(drop=True)[columns]


def detect_habits(
    telemetry_df: pd.DataFrame,
    operator_id: str | None = None,
    min_opportunities: int = config.HABIT_MIN_OPPORTUNITIES,
    min_count: int = config.HABIT_MIN_COUNT,
    z_threshold: float = config.HABIT_Z_THRESHOLD,
) -> list[dict]:
    """Detect the seatbelt-during-truck-wait habit for every operator (or
    just `operator_id` if given).

    Flagging is **relative to the fleet**, not a fixed absolute rate: a
    "habit" is an operator whose frequency is a statistical outlier versus
    their peers (z-score >= `z_threshold`, computed from operators with
    enough opportunities to be comparable) — on top of the absolute
    `min_opportunities` / `min_count` floor, so a single event still never
    qualifies. A fixed absolute cutoff doesn't work well here: idle-block
    telemetry re-samples the seatbelt state every 5 minutes rather than once
    per idle period, so even a low-probability operator can occasionally
    accumulate a non-trivial raw frequency over a long idle block — what
    distinguishes a genuine habit is standing out from everyone else, not
    clearing an arbitrary absolute bar.
    """
    all_opportunities = _task_opportunities(telemetry_df)

    fleet_rows = []
    for op_id, g in all_opportunities.groupby("operator_id"):
        n_opportunities = len(g)
        count = int((g["unbuckled_during_idle"] & g["unbuckled_at_resume"]).sum())
        frequency = count / n_opportunities if n_opportunities else 0.0
        fleet_rows.append(
            {"operator_id": op_id, "count": count, "opportunities": n_opportunities, "frequency": frequency}
        )
    fleet_df = pd.DataFrame(fleet_rows, columns=["operator_id", "count", "opportunities", "frequency"])

    # Fleet mean/std computed only from operators with enough opportunities
    # to be a fair comparison — a 1-opportunity operator's 0%-or-100% rate
    # would otherwise distort the baseline. Pooled (self-inclusive) rather
    # than leave-one-out: with only ~20 operators, excluding the evaluated
    # operator from their own baseline lets the *next*-most-extreme operator
    # look artificially more significant once the true outlier is excluded
    # from their comparison set too, which empirically produced an extra
    # false positive on the real dataset. Pooled keeps one genuine outlier
    # from dragging the whole baseline toward it enough to manufacture a
    # second "outlier" by comparison.
    comparable = fleet_df[fleet_df["opportunities"] >= min_opportunities]
    if len(comparable) > 1:
        fleet_mean = comparable["frequency"].mean()
        # A small floor avoids a division-by-zero / undefined z-score when
        # every operator happens to have the exact same rate (e.g. all 0%)
        # — a real deviation should still register as meaningful, not be
        # silently zeroed out.
        fleet_std = max(comparable["frequency"].std(ddof=0), 0.01)
    else:
        fleet_mean, fleet_std = 0.0, 0.01

    results = []
    for _, row in fleet_df.iterrows():
        if operator_id is not None and row["operator_id"] != operator_id:
            continue

        n_opportunities, count, frequency = int(row["opportunities"]), int(row["count"]), row["frequency"]
        z_score = (frequency - fleet_mean) / fleet_std if n_opportunities >= min_opportunities else 0.0

        is_habit = bool(
            n_opportunities >= min_opportunities and count >= min_count and z_score >= z_threshold
        )

        if is_habit:
            explanation = (
                "Seatbelt was repeatedly removed during truck waits and remained "
                "unfastened when movement resumed, at a rate well above the rest of the fleet "
                f"({count} of {n_opportunities} truck-wait opportunities, {frequency:.0%}, "
                f"z={z_score:.1f} vs. fleet average {fleet_mean:.0%})."
            )
        elif count > 0:
            explanation = (
                f"Seatbelt was unfastened at truck-wait resume {count} time(s) out of "
                f"{n_opportunities} opportunities — not distinct enough from the rest of the fleet to call it a habit."
            )
        else:
            explanation = "No seatbelt-during-truck-wait pattern observed."

        results.append(
            {
                "operator_id": row["operator_id"],
                "habit_type": HABIT_TYPE_SEATBELT_TRUCK_WAIT,
                "count": count,
                "opportunities": n_opportunities,
                "frequency": round(frequency, 3),
                "z_score": round(float(z_score), 2),
                "is_habit": is_habit,
                "explanation": explanation,
            }
        )

    return sorted(results, key=lambda r: r["frequency"], reverse=True)


def get_habit_summary(operator_id: str, telemetry_df: pd.DataFrame) -> dict:
    """Convenience wrapper: the single habit-radar result for one operator,
    with a safe zero-opportunity default when they have none."""
    results = detect_habits(telemetry_df, operator_id=operator_id)
    if results:
        return results[0]
    return {
        "operator_id": operator_id,
        "habit_type": HABIT_TYPE_SEATBELT_TRUCK_WAIT,
        "count": 0,
        "opportunities": 0,
        "frequency": 0.0,
        "z_score": 0.0,
        "is_habit": False,
        "explanation": "No truck-wait opportunities observed for this operator.",
    }
