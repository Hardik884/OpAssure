"""Reset the database to the known-good demo state and verify it.

    python -m simulator.seed                 # drop + recreate tables, load synthetic data, verify
    python -m simulator.seed --verify-only   # just check the current database

Always starts from a clean schema, so running it twice gives the same database.
"""

import argparse
import sys
import time

from sqlalchemy import Engine, func, insert, select
from sqlalchemy.orm import Session

from app.db.init_db import reset_schema
from app.db.session import get_engine
from app.models import (
    GroundTruthLabel, Incident, Machine, NearMiss, Operator, Task, Telemetry, TrainingEvent,
    Weather, WorkerPosition,
)
from simulator import scenarios as demo
from simulator.generate_data import NUM_DAYS, generate_dataset

# Parents before children (foreign keys).
TABLE_MODELS = (
    ("operators", Operator), ("machines", Machine), ("weather", Weather), ("tasks", Task),
    ("telemetry", Telemetry), ("worker_positions", WorkerPosition), ("near_misses", NearMiss),
    ("incidents", Incident), ("ground_truth_labels", GroundTruthLabel),
    ("training_events", TrainingEvent),
)
PLANTED_PROBLEMS = (
    "seatbelt_pattern", "afternoon_slowdown", "machine_degradation",
    "operator_inefficiency", "legitimate_idle", "proximity_near_miss",
)
EXPECTED_OPERATORS = 20
EXPECTED_MACHINES = 8
CHUNK = 5000


def seed(engine: Engine) -> dict[str, int]:
    data = generate_dataset()
    reset_schema(engine)
    with Session(engine) as session, session.begin():
        for table, model in TABLE_MODELS:
            rows = data.get(table, [])
            for i in range(0, len(rows), CHUNK):
                session.execute(insert(model), rows[i : i + CHUNK])
    return {table: len(data.get(table, [])) for table, _ in TABLE_MODELS}


def verify(engine: Engine) -> list[tuple[str, bool, str]]:
    """Return (check, passed, detail) for every check."""
    results: list[tuple[str, bool, str]] = []

    def check(name: str, ok: bool, detail: str) -> None:
        results.append((name, bool(ok), detail))

    with Session(engine) as s:
        count = lambda model: s.scalar(select(func.count()).select_from(model))  # noqa: E731
        n_ops, n_machines, n_tasks, n_tel = count(Operator), count(Machine), count(Task), count(Telemetry)
        check("operators", n_ops == EXPECTED_OPERATORS, f"{n_ops} (expected {EXPECTED_OPERATORS})")
        check("machines", n_machines == EXPECTED_MACHINES, f"{n_machines} (expected {EXPECTED_MACHINES})")
        check("tasks", n_tasks > 1000, f"{n_tasks}")
        check("telemetry", n_tel > 10000, f"{n_tel} rows")
        n_weather = count(Weather)
        check("weather", n_weather == NUM_DAYS * 24, f"{n_weather} hourly rows (expected {NUM_DAYS * 24})")
        skills = sorted(s.scalars(select(Operator.skill).distinct()))
        check("operator skills", skills == ["Beginner", "Expert", "Intermediate"], ", ".join(skills))
        types = sorted(s.scalars(select(Machine.type).distinct()))
        check("machine types", types == ["excavator", "loader"], ", ".join(types))
        check("worker_positions", count(WorkerPosition) > 0, f"{count(WorkerPosition)} rows")
        check("near_misses", count(NearMiss) > 0, f"{count(NearMiss)} rows")
        check("incidents", count(Incident) > 0, f"{count(Incident)} rows")
        check("training_events", count(TrainingEvent) > 0, f"{count(TrainingEvent)} rows")

        op = s.get(Operator, demo.DEMO_OPERATOR_ID)
        check(f"demo operator {demo.DEMO_OPERATOR_ID}", op is not None, op.name if op else "missing")
        machine = s.get(Machine, demo.DEMO_MACHINE_ID)
        check(f"demo machine {demo.DEMO_MACHINE_ID}", machine is not None,
              f"{machine.model}, {machine.age_years}y" if machine else "missing")
        task = s.get(Task, demo.DEMO_TASK_ID)
        linked = (task is not None and task.operator_id == demo.DEMO_OPERATOR_ID
                  and task.machine_id == demo.DEMO_MACHINE_ID)
        check(f"demo task {demo.DEMO_TASK_ID}", linked,
              f"{task.operator_id}/{task.machine_id} at {task.start_time}, est {task.estimated_time_min} min"
              if task else "missing")
        n_demo_tel = s.scalar(select(func.count()).where(Telemetry.task_id == demo.DEMO_TASK_ID))
        check(f"{demo.DEMO_TASK_ID} replay telemetry", n_demo_tel > 0, f"{n_demo_tel} rows")

        labelled = dict(s.execute(select(GroundTruthLabel.problem, func.count()).group_by(GroundTruthLabel.problem)).all())
        for problem in PLANTED_PROBLEMS:
            check(f"ground truth: {problem}", labelled.get(problem, 0) > 0, f"{labelled.get(problem, 0)} labels")
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify-only", action="store_true", help="only verify the current database")
    args = parser.parse_args()
    engine = get_engine()

    if not args.verify_only:
        started = time.perf_counter()
        counts = seed(engine)
        print(f"Seeded database in {time.perf_counter() - started:.1f}s:")
        for table, n in counts.items():
            print(f"  {table:22s} {n:>7d}")

    results = verify(engine)
    print("Verification:")
    for name, ok, detail in results:
        print(f"  [{'PASS' if ok else 'FAIL'}] {name}: {detail}")
    failed = [name for name, ok, _ in results if not ok]
    print("VERIFY: PASS" if not failed else f"VERIFY: FAIL ({', '.join(failed)})")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
