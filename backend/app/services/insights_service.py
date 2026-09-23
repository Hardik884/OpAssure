"""Deterministic operator metrics and habit detection (Operator Twin inputs, Habit Radar v0).

Everything is computed with SQL aggregates over history *before today* (so the
scripted demo-day telemetry never leaks into the history). Metrics are compared
with the fleet median; fuel is normalised per machine so a worn machine (EXC003)
is not blamed on whoever drives it.
"""

from collections import defaultdict
from datetime import datetime
from statistics import median

from sqlalchemy import Integer, and_, case, cast, extract, func, select
from sqlalchemy.orm import Session

from app.models import Incident, NearMiss, Operator, Task, Telemetry, TrainingEvent

METRIC_KEYS = (
    "tasks_completed", "operating_hours", "avg_actual_vs_estimate", "avg_eta_error_min",
    "fuel_per_cycle_l", "fuel_vs_fleet_ratio", "avoidable_idle_min_per_hour",
    "legitimate_idle_min_per_hour", "harsh_events_per_hour", "seatbelt_violations",
    "unbelted_idle_samples", "afternoon_pace_ratio",
)

# Habit thresholds (deterministic, documented in docs/api).
SEATBELT_MIN_VIOLATIONS = 3
IDLE_VS_FLEET = 1.5
HARSH_VS_FLEET = 2.0
AFTERNOON_PACE_RATIO = 1.10
FUEL_VS_SKILL_PEERS = 1.20


def _grouped_rows(db: Session, before: datetime, operator_id: str | None = None, by_hour: bool = False):
    hour = cast(extract("hour", Telemetry.timestamp), Integer)
    bucket = hour if by_hour else case((hour < 12, "am"), (hour >= 15, "pm"), else_="mid")
    q = select(
        Telemetry.operator_id, Telemetry.machine_id, bucket.label("bucket"),
        func.sum(Telemetry.fuel_used_l).label("fuel"),
        func.sum(Telemetry.load_cycles).label("cycles"),
        func.sum(Telemetry.avg_cycle_time_s).label("cycle_sum"),
        func.count(Telemetry.avg_cycle_time_s).label("cycle_n"),
        func.sum(case((Telemetry.idle_reason == "avoidable", Telemetry.idling_time_min), else_=0)).label("idle_avoidable"),
        func.sum(case((Telemetry.idle_reason == "truck_wait", Telemetry.idling_time_min), else_=0)).label("idle_truck"),
        func.sum(Telemetry.harsh_events).label("harsh"),
        func.sum(case((Telemetry.safety_alert == "seatbelt", 1), else_=0)).label("alert_seatbelt"),
        func.sum(case((Telemetry.safety_alert == "unattended_machine", 1), else_=0)).label("alert_unattended"),
        func.sum(case((Telemetry.safety_alert == "avoidable_idle", 1), else_=0)).label("alert_idle"),
        func.sum(case((and_(Telemetry.seatbelt_status == "unfastened", Telemetry.machine_moving.is_(False)), 1),
                      else_=0)).label("unbelted_idle"),
    ).where(Telemetry.timestamp < before).group_by(Telemetry.operator_id, Telemetry.machine_id, bucket)
    if operator_id:
        q = q.where(Telemetry.operator_id == operator_id)
    return db.execute(q).mappings().all()


def _machine_baselines(rows) -> tuple[dict, dict]:
    fuel, cycles, csum, cn = defaultdict(float), defaultdict(float), defaultdict(float), defaultdict(float)
    for r in rows:
        m = r["machine_id"]
        fuel[m] += r["fuel"] or 0
        cycles[m] += r["cycles"] or 0
        csum[m] += r["cycle_sum"] or 0
        cn[m] += r["cycle_n"] or 0
    fpc = {m: fuel[m] / cycles[m] for m in fuel if cycles[m]}
    avg_cycle = {m: csum[m] / cn[m] for m in csum if cn[m]}
    return fpc, avg_cycle


def fleet_metrics(db: Session, before: datetime) -> dict[str, dict]:
    """operator_id -> metrics dict (METRIC_KEYS + alert counts), for every operator."""
    rows = _grouped_rows(db, before)
    machine_fpc, machine_cycle = _machine_baselines(rows)

    acc: dict[str, dict] = defaultdict(lambda: defaultdict(float))
    for r in rows:
        a = acc[r["operator_id"]]
        for key in ("fuel", "cycles", "idle_avoidable", "idle_truck", "harsh", "alert_seatbelt",
                    "alert_unattended", "alert_idle", "unbelted_idle"):
            a[key] += r[key] or 0
        a["expected_fuel"] += (r["cycles"] or 0) * machine_fpc.get(r["machine_id"], 0)
        if r["bucket"] in ("am", "pm") and r["cycle_n"]:
            a[f"{r['bucket']}_norm_sum"] += (r["cycle_sum"] or 0) / machine_cycle[r["machine_id"]]
            a[f"{r['bucket']}_n"] += r["cycle_n"]

    task_rows = db.execute(
        select(Task.operator_id, func.count(), func.sum(Task.actual_time_min),
               func.avg(Task.actual_time_min / Task.estimated_time_min),
               func.avg(Task.actual_time_min - Task.estimated_time_min))
        .where(Task.status == "completed", Task.start_time < before).group_by(Task.operator_id)
    ).all()
    tasks = {op: (n, minutes, ratio, err) for op, n, minutes, ratio, err in task_rows}

    out = {}
    for op in db.scalars(select(Operator.operator_id).order_by(Operator.operator_id)):
        a = acc.get(op, defaultdict(float))
        n, minutes, ratio, err = tasks.get(op, (0, 0, None, None))
        hours = (minutes or 0) / 60
        per_hour = (lambda v: round(v / hours, 3) if hours else None)  # noqa: E731
        out[op] = {
            "tasks_completed": n,
            "operating_hours": round(hours, 1),
            "avg_actual_vs_estimate": round(ratio, 3) if ratio is not None else None,
            "avg_eta_error_min": round(err, 1) if err is not None else None,
            "fuel_per_cycle_l": round(a["fuel"] / a["cycles"], 4) if a["cycles"] else None,
            "fuel_vs_fleet_ratio": round(a["fuel"] / a["expected_fuel"], 3) if a["expected_fuel"] else None,
            "avoidable_idle_min_per_hour": per_hour(a["idle_avoidable"]),
            "legitimate_idle_min_per_hour": per_hour(a["idle_truck"]),
            "harsh_events_per_hour": per_hour(a["harsh"]),
            "seatbelt_violations": int(a["alert_seatbelt"]),
            "unbelted_idle_samples": int(a["unbelted_idle"]),
            "afternoon_pace_ratio": (round((a["pm_norm_sum"] / a["pm_n"]) / (a["am_norm_sum"] / a["am_n"]), 3)
                                     if a["pm_n"] and a["am_n"] else None),
            "alerts": {"seatbelt": int(a["alert_seatbelt"]), "unattended_machine": int(a["alert_unattended"]),
                       "avoidable_idle": int(a["alert_idle"])},
        }
    return out


def fleet_medians(metrics: dict[str, dict]) -> dict:
    result = {}
    for key in METRIC_KEYS:
        vals = [m[key] for m in metrics.values() if m[key] is not None]
        result[key] = round(median(vals), 3) if vals else None
    return result


def detect_habits(m: dict, fleet: dict, skill_peer_fuel_ratio: float | None) -> list[dict]:
    """Deterministic Habit Radar: [{habit_type, count, severity, explanation, metric_name, metric, fleet_metric}]."""
    habits = []

    def add(habit_type, count, severity, explanation, metric_name, metric, fleet_metric):
        habits.append({"habit_type": habit_type, "count": count, "severity": severity, "explanation": explanation,
                       "metric_name": metric_name, "metric": metric, "fleet_metric": fleet_metric})

    if m["seatbelt_violations"] >= SEATBELT_MIN_VIOLATIONS:
        add("seatbelt", m["seatbelt_violations"], "critical",
            f"Moved with seatbelt unfastened {m['seatbelt_violations']} times, usually right after a truck wait "
            f"(fleet median {fleet['seatbelt_violations']:g}).",
            "seatbelt_violations", m["seatbelt_violations"], fleet["seatbelt_violations"])
    rate, base = m["avoidable_idle_min_per_hour"], fleet["avoidable_idle_min_per_hour"]
    if rate is not None and base and rate > IDLE_VS_FLEET * base:
        add("avoidable_idle", round(rate * m["operating_hours"]), "warning",
            f"{rate:.1f} min/h of avoidable idle vs fleet {base:.1f} min/h. Truck waits are not counted.",
            "avoidable_idle_min_per_hour", rate, base)
    rate, base = m["harsh_events_per_hour"], fleet["harsh_events_per_hour"]
    if rate is not None and base and rate > HARSH_VS_FLEET * base:
        add("harsh_events", round(rate * m["operating_hours"]), "warning",
            f"{rate:.2f} harsh swings/brakes per hour vs fleet {base:.2f}.",
            "harsh_events_per_hour", rate, base)
    ratio = m["afternoon_pace_ratio"]
    if ratio is not None and ratio >= AFTERNOON_PACE_RATIO:
        add("afternoon_slowdown", None, "warning",
            f"Cycles are {ratio - 1:.0%} slower after 15:00 than before noon (fleet {fleet['afternoon_pace_ratio'] - 1:.0%}).",
            "afternoon_pace_ratio", ratio, fleet["afternoon_pace_ratio"])
    if skill_peer_fuel_ratio is not None and skill_peer_fuel_ratio >= FUEL_VS_SKILL_PEERS:
        add("fuel_inefficiency", None, "warning",
            f"Uses {skill_peer_fuel_ratio - 1:.0%} more fuel per bucket than operators of the same skill, "
            f"on the same machines.",
            "fuel_vs_fleet_ratio", m["fuel_vs_fleet_ratio"], fleet["fuel_vs_fleet_ratio"])
    return habits


def operator_habits(db: Session, operator: Operator, before: datetime) -> tuple[dict, dict, list[dict]]:
    """(operator metrics, fleet medians, habits)."""
    metrics = fleet_metrics(db, before)
    fleet = fleet_medians(metrics)
    skills = dict(db.execute(select(Operator.operator_id, Operator.skill)).all())
    peers = [v["fuel_vs_fleet_ratio"] for op, v in metrics.items()
             if skills[op] == operator.skill and op != operator.operator_id and v["fuel_vs_fleet_ratio"]]
    mine = metrics[operator.operator_id]
    peer_ratio = (mine["fuel_vs_fleet_ratio"] / median(peers)) if peers and mine["fuel_vs_fleet_ratio"] else None
    return mine, fleet, detect_habits(mine, fleet, peer_ratio)


def operator_insights(db: Session, operator: Operator, before: datetime) -> dict:
    mine, fleet, habits = operator_habits(db, operator, before)
    all_rows = _grouped_rows(db, before)
    machine_fpc, machine_cycle = _machine_baselines(all_rows)

    hourly = defaultdict(lambda: [0.0, 0.0, 0])  # hour -> [raw cycle sum, normalised sum, n]
    for r in _grouped_rows(db, before, operator.operator_id, by_hour=True):
        if r["cycle_n"]:
            h = hourly[int(r["bucket"])]
            h[0] += r["cycle_sum"]
            h[1] += r["cycle_sum"] / machine_cycle[r["machine_id"]]
            h[2] += r["cycle_n"]
    pace_by_hour = [{"hour": h, "avg_cycle_time_s": round(v[0] / v[2], 2), "pace_index": round(v[1] / v[2], 3),
                     "samples": v[2]} for h, v in sorted(hourly.items())]

    per_machine = defaultdict(lambda: [0.0, 0.0])
    for r in all_rows:
        if r["operator_id"] == operator.operator_id:
            per_machine[r["machine_id"]][0] += r["fuel"] or 0
            per_machine[r["machine_id"]][1] += r["cycles"] or 0
    task_counts = dict(db.execute(
        select(Task.machine_id, func.count()).where(Task.operator_id == operator.operator_id,
                                                    Task.status == "completed", Task.start_time < before)
        .group_by(Task.machine_id)).all())
    machines = [{"machine_id": m, "tasks": task_counts.get(m, 0),
                 "fuel_per_cycle_l": round(f / c, 4) if c else None,
                 "fleet_fuel_per_cycle_l": round(machine_fpc[m], 4) if m in machine_fpc else None}
                for m, (f, c) in sorted(per_machine.items())]

    near_misses = db.scalar(select(func.count()).select_from(NearMiss)
                            .where(NearMiss.operator_id == operator.operator_id, NearMiss.timestamp < before))
    incidents = db.scalar(select(func.count()).select_from(Incident).where(Incident.operator_id == operator.operator_id))
    training = db.scalars(select(TrainingEvent).where(TrainingEvent.operator_id == operator.operator_id)
                          .order_by(TrainingEvent.timestamp)).all()
    return {
        "operator": operator,
        "history_until": before,
        "summary": {k: mine[k] for k in METRIC_KEYS},
        "fleet": fleet,
        "pace_by_hour": pace_by_hour,
        "machines": machines,
        "safety": {"alerts": mine["alerts"], "near_misses": near_misses, "incidents": incidents},
        "habits": habits,
        "training": training,
    }
