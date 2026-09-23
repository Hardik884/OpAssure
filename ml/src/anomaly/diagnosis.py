"""Machine-vs-operator fuel diagnosis: distinguishes a machine that's burning
extra fuel for everyone who runs it (a machine problem) from an operator
who burns extra fuel on every machine they run (an operator problem).

The evidence requirement for each is symmetric: elevated fuel use has to
show up across *multiple* of the other entity type — one operator's one bad
day on a machine is not "machine degradation", and one task on a machine
that runs hot is not "operator inefficiency". `config.DIAGNOSIS_MIN_DISTINCT_ENTITIES`
sets that bar.
"""

import pandas as pd

from src.common import config


def _task_fuel_per_moving_min(tasks_df: pd.DataFrame, telemetry_df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        telemetry_df.groupby("task_id")
        .agg(fuel_used_l=("fuel_used_l", "sum"), moving_minutes=("machine_moving", "sum"))
        .reset_index()
    )
    agg["moving_minutes"] = agg["moving_minutes"].replace(0, pd.NA)
    agg["fuel_per_moving_min"] = agg["fuel_used_l"] / agg["moving_minutes"]

    return tasks_df[["task_id", "operator_id", "machine_id"]].merge(agg, on="task_id", how="inner").dropna(
        subset=["fuel_per_moving_min"]
    )


def diagnose_fuel_source(
    tasks_df: pd.DataFrame,
    telemetry_df: pd.DataFrame,
    min_distinct_entities: int = config.DIAGNOSIS_MIN_DISTINCT_ENTITIES,
    elevated_ratio: float = config.DIAGNOSIS_ELEVATED_RATIO,
) -> list[dict]:
    """Return every machine and operator whose fuel use is consistently
    elevated with enough cross-entity evidence to be explainable, sorted by
    strength of evidence (highest ratio first)."""
    task_fuel = _task_fuel_per_moving_min(tasks_df, telemetry_df)
    fleet_mean = task_fuel["fuel_per_moving_min"].mean()
    if not fleet_mean or pd.isna(fleet_mean):
        return []

    findings = []

    # --- Case A: a machine elevated across multiple operators --------------
    per_machine_operator = task_fuel.groupby(["machine_id", "operator_id"])["fuel_per_moving_min"].mean()
    for machine_id, by_operator in per_machine_operator.groupby(level="machine_id"):
        n_operators = len(by_operator)
        if n_operators < min_distinct_entities:
            continue
        machine_mean = by_operator.mean()
        ratio = machine_mean / fleet_mean
        n_elevated = (by_operator / fleet_mean >= elevated_ratio).sum()
        # Require the elevation to show up for MOST of the operators who
        # used it, not just the overall average being dragged up by one.
        if ratio >= elevated_ratio and n_elevated / n_operators >= 0.6:
            findings.append(
                {
                    "source": "machine",
                    "machine_id": machine_id,
                    "evidence": (
                        f"Fuel per moving-minute is consistently elevated across {n_operators} distinct "
                        f"operators ({ratio - 1:+.0%} vs. fleet average)."
                    ),
                    "ratio_vs_fleet": round(float(ratio), 3),
                    "n_distinct_entities": int(n_operators),
                }
            )

    # --- Case B: an operator elevated across multiple machines --------------
    per_operator_machine = task_fuel.groupby(["operator_id", "machine_id"])["fuel_per_moving_min"].mean()
    for operator_id, by_machine in per_operator_machine.groupby(level="operator_id"):
        n_machines = len(by_machine)
        if n_machines < min_distinct_entities:
            continue
        operator_mean = by_machine.mean()
        ratio = operator_mean / fleet_mean
        n_elevated = (by_machine / fleet_mean >= elevated_ratio).sum()
        if ratio >= elevated_ratio and n_elevated / n_machines >= 0.6:
            findings.append(
                {
                    "source": "operator",
                    "operator_id": operator_id,
                    "evidence": (
                        f"Fuel use is consistently elevated across {n_machines} distinct machines "
                        f"({ratio - 1:+.0%} vs. fleet average)."
                    ),
                    "ratio_vs_fleet": round(float(ratio), 3),
                    "n_distinct_entities": int(n_machines),
                }
            )

    return sorted(findings, key=lambda f: f["ratio_vs_fleet"], reverse=True)
