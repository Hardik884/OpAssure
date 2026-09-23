"""Tests for machine-vs-operator fuel diagnosis against the planted patterns."""

from src.anomaly.diagnosis import diagnose_fuel_source
from src.common import config
from src.evaluation.behaviour_eval import evaluate_diagnosis


def test_machine_degradation_is_diagnosed(tables):
    findings = diagnose_fuel_source(tables["tasks"], tables["telemetry"])
    machine_findings = [f for f in findings if f["source"] == "machine"]
    machine_ids = {f["machine_id"] for f in machine_findings}
    assert config.DEGRADING_MACHINE_ID in machine_ids

    finding = next(f for f in machine_findings if f["machine_id"] == config.DEGRADING_MACHINE_ID)
    assert finding["ratio_vs_fleet"] > config.DIAGNOSIS_ELEVATED_RATIO
    assert finding["n_distinct_entities"] >= config.DIAGNOSIS_MIN_DISTINCT_ENTITIES
    assert "operator" in finding["evidence"].lower()


def test_operator_inefficiency_is_diagnosed(tables):
    findings = diagnose_fuel_source(tables["tasks"], tables["telemetry"])
    operator_findings = [f for f in findings if f["source"] == "operator"]
    operator_ids = {f["operator_id"] for f in operator_findings}
    assert config.INEFFICIENT_OPERATOR_ID in operator_ids

    finding = next(f for f in operator_findings if f["operator_id"] == config.INEFFICIENT_OPERATOR_ID)
    assert finding["ratio_vs_fleet"] > config.DIAGNOSIS_ELEVATED_RATIO
    assert finding["n_distinct_entities"] >= config.DIAGNOSIS_MIN_DISTINCT_ENTITIES
    assert "machine" in finding["evidence"].lower()


def test_diagnosis_requires_minimum_distinct_entities(tables):
    """Raising the minimum entity bar past what any single machine/operator
    has evidence for should shrink (not error on) the result set."""
    findings_strict = diagnose_fuel_source(tables["tasks"], tables["telemetry"], min_distinct_entities=100)
    assert findings_strict == []


def test_ground_truth_evaluation_confirms_both_planted_cases(tables):
    report = evaluate_diagnosis(tables["tasks"], tables["telemetry"])
    assert report["machine_correctly_flagged"] is True
    assert report["operator_correctly_flagged"] is True
    assert report["n_machine_false_positives"] == 0
    assert report["n_operator_false_positives"] == 0
