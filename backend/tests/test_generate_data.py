"""Synthetic generator: scale, demo entities, planted problems, determinism. No DB needed."""

import hashlib
import json
from collections import Counter
from statistics import mean

import pytest

from simulator import scenarios as demo
from simulator.generate_data import (
    DEGRADING_MACHINE, INEFFICIENT_OPERATOR, NEAR_MISS_MACHINE, NEAR_MISS_WORKER, NUM_DAYS, SEATBELT_HABIT_OPERATOR,
    generate_dataset,
)


@pytest.fixture(scope="module")
def data():
    return generate_dataset()


def _digest(dataset) -> str:
    return hashlib.sha256(json.dumps(dataset, sort_keys=True, default=str).encode()).hexdigest()


def test_scale(data):
    assert len(data["operators"]) == 20
    assert len(data["machines"]) == 8
    assert len(data["weather"]) == NUM_DAYS * 24
    days = {t["start_time"].date() for t in data["tasks"]}
    assert len(days) == NUM_DAYS
    assert Counter(o["skill"] for o in data["operators"]) == {"Beginner": 6, "Intermediate": 8, "Expert": 6}
    assert {m["type"] for m in data["machines"]} == {"excavator", "loader"}
    assert len({m["age_years"] for m in data["machines"]}) > 1


def test_demo_entities(data):
    task = next(t for t in data["tasks"] if t["task_id"] == demo.DEMO_TASK_ID)
    assert task["operator_id"] == demo.DEMO_OPERATOR_ID
    assert task["machine_id"] == demo.DEMO_MACHINE_ID
    assert task["estimated_time_min"] == 45
    rows = [r for r in data["telemetry"] if r["task_id"] == demo.DEMO_TASK_ID]
    assert 52 <= len(rows) <= 58  # ETA story: plan 45 -> actual 52-58 min
    alerts = [r["safety_alert"] for r in rows]
    assert "seatbelt" in alerts


def test_ids_unique_and_referentially_sound(data):
    task_ids = [t["task_id"] for t in data["tasks"]]
    assert len(task_ids) == len(set(task_ids))
    ops = {o["operator_id"] for o in data["operators"]}
    machines = {m["machine_id"] for m in data["machines"]}
    for r in data["telemetry"]:
        assert r["operator_id"] in ops and r["machine_id"] in machines
    assert {r["task_id"] for r in data["telemetry"]} <= set(task_ids)


def test_telemetry_interval_is_5_to_15_min_outside_events(data):
    by_task: dict[str, list] = {}
    for r in data["telemetry"]:
        by_task.setdefault(r["task_id"], []).append(r["timestamp"])
    gaps = [
        (b - a).total_seconds() / 60
        for task_id, ts in by_task.items() if task_id != demo.DEMO_TASK_ID
        for a, b in zip(sorted(ts), sorted(ts)[1:])
    ]
    assert max(gaps) <= 15


def test_planted_seatbelt_habit(data):
    unbelted = Counter(r["operator_id"] for r in data["telemetry"]
                       if r["seatbelt_status"] == "unfastened" and r["task_id"] != demo.DEMO_TASK_ID)
    top, n = unbelted.most_common(1)[0]
    assert top == SEATBELT_HABIT_OPERATOR
    assert n > 3 * unbelted.most_common(2)[1][1]


def test_planted_machine_degradation(data):
    def fuel_per_cycle(machine_id, first_days):
        rows = [r for r in data["telemetry"] if r["machine_id"] == machine_id and r["load_cycles"] > 0
                and ((r["timestamp"].day <= 10 and r["timestamp"].month == 5) == first_days)
                and r["task_id"] != demo.DEMO_TASK_ID]
        return sum(r["fuel_used_l"] for r in rows) / sum(r["load_cycles"] for r in rows)

    growth = fuel_per_cycle(DEGRADING_MACHINE, False) / fuel_per_cycle(DEGRADING_MACHINE, True)
    other = fuel_per_cycle("EXC002", False) / fuel_per_cycle("EXC002", True)
    assert growth > other + 0.1


def test_planted_operator_inefficiency(data):
    fuel, cycles = Counter(), Counter()
    for r in data["telemetry"]:
        if r["machine_id"] != DEGRADING_MACHINE:
            fuel[r["operator_id"]] += r["fuel_used_l"]
            cycles[r["operator_id"]] += r["load_cycles"]
    skill = {o["operator_id"]: o["skill"] for o in data["operators"]}
    peers = [fuel[o] / cycles[o] for o in fuel if skill[o] == skill[INEFFICIENT_OPERATOR] and o != INEFFICIENT_OPERATOR]
    assert fuel[INEFFICIENT_OPERATOR] / cycles[INEFFICIENT_OPERATOR] > 1.2 * mean(peers)
    machines_used = {r["machine_id"] for r in data["telemetry"] if r["operator_id"] == INEFFICIENT_OPERATOR}
    assert len(machines_used) >= 3


def test_planted_afternoon_slowdown(data):
    def avg_cycle(op, afternoon):
        vals = [r["avg_cycle_time_s"] for r in data["telemetry"]
                if r["operator_id"] == op and r["avg_cycle_time_s"] and r["machine_id"].startswith("EXC")
                and r["machine_id"] != DEGRADING_MACHINE and (r["timestamp"].hour >= 15) == afternoon]
        return mean(vals)

    assert avg_cycle("OP1012", True) > 1.08 * avg_cycle("OP1012", False)


def test_near_misses_and_ground_truth(data):
    assert len(data["near_misses"]) >= 10
    assert all(n["worker_id"] == NEAR_MISS_WORKER and n["machine_id"] == NEAR_MISS_MACHINE
               for n in data["near_misses"])
    assert all(n["severity"] == "critical" for n in data["near_misses"])
    problems = {g["problem"] for g in data["ground_truth_labels"]}
    assert problems == {"seatbelt_pattern", "afternoon_slowdown", "machine_degradation",
                        "operator_inefficiency", "legitimate_idle", "proximity_near_miss"}
    idle_labels = [g for g in data["ground_truth_labels"] if g["problem"] == "legitimate_idle"]
    assert idle_labels and all(g["task_id"] for g in idle_labels)


def test_incidents_have_telemetry_snapshot(data):
    assert data["incidents"]
    assert all(i["telemetry_snapshot"] for i in data["incidents"])


def test_deterministic(data):
    assert _digest(generate_dataset()) == _digest(data)
