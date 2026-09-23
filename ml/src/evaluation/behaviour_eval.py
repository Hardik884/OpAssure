"""Evaluate the behaviour + safety intelligence subsystem against
`data/ground_truth/` — not just "does it run", but "does it find the right
planted operators/machines, and does it ever falsely blame an operator for
a legitimate truck-wait idle".
"""

import pandas as pd
from sklearn.metrics import precision_recall_fscore_support

from src.anomaly.diagnosis import diagnose_fuel_source
from src.anomaly.habit_radar import detect_habits
from src.anomaly.idle_shield import classify_idle, classify_task_idle
from src.common import config


def evaluate_habit_radar(telemetry_df: pd.DataFrame, operators_df: pd.DataFrame) -> dict:
    """Treat every operator as a binary classification case: should this
    operator be flagged as having the seatbelt-during-truck-wait habit?
    Ground truth positive = only `config.SEATBELT_HABIT_OPERATOR_ID`
    (see `ground_truth_labels.csv`, pattern `seatbelt_habit`)."""
    results = detect_habits(telemetry_df)
    flagged = {r["operator_id"] for r in results if r["is_habit"]}

    all_operators = list(operators_df["operator_id"])
    y_true = [op == config.SEATBELT_HABIT_OPERATOR_ID for op in all_operators]
    y_pred = [op in flagged for op in all_operators]

    precision, recall, f1, _ = precision_recall_fscore_support(
        y_true, y_pred, average="binary", zero_division=0
    )
    return {
        "flagged_operators": sorted(flagged),
        "expected_operator": config.SEATBELT_HABIT_OPERATOR_ID,
        "correctly_flagged": config.SEATBELT_HABIT_OPERATOR_ID in flagged,
        "n_false_positives": len(flagged - {config.SEATBELT_HABIT_OPERATOR_ID}),
        "precision": round(float(precision), 3),
        "recall": round(float(recall), 3),
        "f1": round(float(f1), 3),
    }


def evaluate_idle_shield(telemetry_df: pd.DataFrame, task_ground_truth_df: pd.DataFrame) -> dict:
    """Task-level: does classify_task_idle's dominant-type call match
    `task_ground_truth.is_legitimate_idle_dominant`? Also explicitly reports
    the "legitimate truck-wait idle falsely blamed on the operator" rate —
    this must be exactly 0.0 given the hard no-blame rule in classify_idle().
    """
    idle_telemetry = telemetry_df[telemetry_df["idling_time_min"] > 0]
    task_ids_with_idle = idle_telemetry["task_id"].unique()

    predictions = {tid: classify_task_idle(tid, telemetry_df) for tid in task_ids_with_idle}
    gt = task_ground_truth_df.set_index("task_id")

    y_true, y_pred = [], []
    false_blame_count = 0
    truck_wait_task_count = 0

    for tid, pred in predictions.items():
        if tid not in gt.index:
            continue
        true_legit = bool(gt.loc[tid, "is_legitimate_idle_dominant"])
        pred_legit = pred["dominant_idle_type"] == "legitimate"
        y_true.append(true_legit)
        y_pred.append(pred_legit)

        # Does this task have ANY waiting_for_truck idle minutes at all?
        has_truck_wait = (
            telemetry_df[(telemetry_df["task_id"] == tid) & (telemetry_df["idle_reason"] == "waiting_for_truck")]
        )
        if len(has_truck_wait) > 0:
            truck_wait_task_count += 1
            # False blame: this task's truck-wait idle minutes were
            # individually classified as avoidable by classify_idle (would
            # violate the hard no-blame rule if it ever happened).
            row_level_blame = any(
                classify_idle(row)["idle_type"] == "avoidable" for _, row in has_truck_wait.iterrows()
            )
            if row_level_blame:
                false_blame_count += 1

    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    accuracy = sum(t == p for t, p in zip(y_true, y_pred)) / len(y_true) if y_true else 0.0

    # Generic false-positive rate for the "legitimate" class: predicted
    # legitimate but actually avoidable, i.e. FP / (FP + TN).
    fp = sum(p and not t for t, p in zip(y_true, y_pred))
    tn = sum(not p and not t for t, p in zip(y_true, y_pred))
    false_positive_rate = round(fp / (fp + tn), 3) if (fp + tn) else 0.0

    return {
        "n_tasks_evaluated": len(y_true),
        "accuracy": round(accuracy, 3),
        "precision": round(float(precision), 3),
        "recall": round(float(recall), 3),
        "f1": round(float(f1), 3),
        "false_positive_rate": false_positive_rate,
        "accuracy_note": (
            "classify_idle() reads idle_reason, the only per-row signal real telemetry provides. "
            "task_ground_truth.is_legitimate_idle_dominant is computed from a separate, finer-grained "
            "generator signal (planned-vs-extra idle minutes) that a real deployment wouldn't have "
            "either — so a gap here reflects a genuinely harder, more realistic evaluation, not a "
            "classify_idle() defect. The critical, explicitly required guarantee is the no-blame rate below."
        ),
        "truck_wait_tasks_evaluated": truck_wait_task_count,
        "legitimate_idle_falsely_blamed_count": false_blame_count,
        "legitimate_idle_falsely_blamed_rate": round(
            false_blame_count / truck_wait_task_count, 4
        ) if truck_wait_task_count else 0.0,
    }


def evaluate_diagnosis(tasks_df: pd.DataFrame, telemetry_df: pd.DataFrame) -> dict:
    """Does diagnose_fuel_source() find the planted degrading machine and
    the planted inefficient operator?"""
    findings = diagnose_fuel_source(tasks_df, telemetry_df)
    machine_ids = {f["machine_id"] for f in findings if f["source"] == "machine"}
    operator_ids = {f["operator_id"] for f in findings if f["source"] == "operator"}

    return {
        "machine_findings": [f for f in findings if f["source"] == "machine"],
        "operator_findings": [f for f in findings if f["source"] == "operator"],
        "expected_machine": config.DEGRADING_MACHINE_ID,
        "expected_operator": config.INEFFICIENT_OPERATOR_ID,
        "machine_correctly_flagged": config.DEGRADING_MACHINE_ID in machine_ids,
        "operator_correctly_flagged": config.INEFFICIENT_OPERATOR_ID in operator_ids,
        "n_machine_false_positives": len(machine_ids - {config.DEGRADING_MACHINE_ID}),
        "n_operator_false_positives": len(operator_ids - {config.INEFFICIENT_OPERATOR_ID}),
    }


def evaluate_seatbelt_critical_detection(telemetry_df: pd.DataFrame) -> dict:
    """Sanity-check that the hard critical-risk rule (moving + unbuckled)
    exactly matches the data's own `safety_alert` column — this should be
    ~perfect by construction, and a meaningful regression test if it isn't."""
    from src.safety.risk import calculate_risk

    sample = telemetry_df.sample(n=min(2000, len(telemetry_df)), random_state=config.SEED)
    y_true, y_pred = [], []
    for _, row in sample.iterrows():
        result = calculate_risk(seatbelt_status=row["seatbelt_status"], machine_moving=bool(row["machine_moving"]))
        y_true.append(bool(row["safety_alert"]))
        y_pred.append(result["risk_level"] == "critical")

    precision, recall, f1, _ = precision_recall_fscore_support(y_true, y_pred, average="binary", zero_division=0)
    return {
        "n_sampled": len(sample),
        "precision": round(float(precision), 3),
        "recall": round(float(recall), 3),
        "f1": round(float(f1), 3),
    }


def evaluate_all(tables: dict) -> dict:
    """Run every behaviour/safety evaluation and return one combined report."""
    return {
        "habit_radar": evaluate_habit_radar(tables["telemetry"], tables["operators"]),
        "idle_shield": evaluate_idle_shield(tables["telemetry"], tables["task_ground_truth"]),
        "diagnosis": evaluate_diagnosis(tables["tasks"], tables["telemetry"]),
        "seatbelt_critical_detection": evaluate_seatbelt_critical_detection(tables["telemetry"]),
    }
