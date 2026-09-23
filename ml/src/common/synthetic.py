"""Deterministic synthetic data generator (fallback dataset).

The backend's own simulator (`backend/simulator/`) is not implemented yet, so
this module produces the smallest useful, fully deterministic dataset the ML
layer needs to build features against: `operators`, `machines`, `weather`,
`tasks`, `telemetry`, `worker_positions`, `near_misses`, `incidents`,
`training_events`, plus two ground-truth label tables.

Everything here is seeded (`config.SEED`) — re-running `generate_all()` always
produces byte-identical output. This is not meant to be a realistic physics
simulation; it's meant to be *just* realistic enough to exercise ETA,
Operator Twin, anomaly, and safety features, with the six planted patterns
from CLAUDE.md §6 present and labeled.
"""

from datetime import timedelta

import numpy as np
import pandas as pd

from src.common import config
from src.common.geo import distance_m
from src.common.io import write_csv

# ---------------------------------------------------------------------------
# Static reference data
# ---------------------------------------------------------------------------

SKILLS = ["novice", "intermediate", "expert"]
SKILL_FACTOR = {"novice": 0.85, "intermediate": 1.00, "expert": 1.18}
SKILL_PROBS = [0.25, 0.50, 0.25]

MACHINE_TYPES = ["excavator", "dozer", "loader"]
MACHINE_TYPE_PROBS = [0.5, 0.25, 0.25]

TASK_TYPES = ["excavation", "loading", "grading", "trenching", "hauling"]
TRUCK_DEPENDENT_TYPES = {"loading", "hauling"}
TASK_VOLUME_RANGE_M3 = {
    "excavation": (80, 220),
    "loading": (40, 120),
    "grading": (60, 150),
    "trenching": (50, 130),
    "hauling": (30, 90),
}
BUCKET_SIZE_M3 = 1.5
BASE_CYCLE_S = 30.0

WEATHER_CONDITIONS = ["clear", "cloudy", "rain", "storm"]
WEATHER_PROBS = [0.55, 0.25, 0.16, 0.04]
WEATHER_PENALTY = {"clear": 0.0, "cloudy": 0.03, "rain": 0.15, "storm": 0.30}

ZONES = ["zone_a", "zone_b", "zone_c", "zone_d"]
SITE_ORIGIN = (40.0000, -105.0000)
ZONE_OFFSET = {
    "zone_a": (0.0000, 0.0000),
    "zone_b": (0.0010, 0.0005),
    "zone_c": (-0.0008, 0.0012),
    "zone_d": (0.0005, -0.0010),
}


def _zone_coords(zone: str) -> tuple[float, float]:
    dlat, dlon = ZONE_OFFSET[zone]
    return SITE_ORIGIN[0] + dlat, SITE_ORIGIN[1] + dlon


# ---------------------------------------------------------------------------
# operators / machines / weather
# ---------------------------------------------------------------------------


def generate_operators(rng: np.random.Generator) -> pd.DataFrame:
    n = config.N_OPERATORS
    operator_ids = [f"OP{1001 + i}" for i in range(n)]
    skills = rng.choice(SKILLS, size=n, p=SKILL_PROBS)
    base_speed = np.clip(rng.normal(1.0, 0.08, n), 0.75, 1.25)
    fatigue_start_hour = rng.integers(13, 16, n)  # 1pm-3pm, per CLAUDE.md §6
    heat_sensitivity = rng.uniform(0.05, 0.35, n)
    rain_sensitivity = rng.uniform(0.02, 0.25, n)
    belt_skip_probability_when_idle = rng.uniform(0.01, 0.05, n)

    df = pd.DataFrame(
        {
            "operator_id": operator_ids,
            "name": [f"Operator {i + 1}" for i in range(n)],
            "skill": skills,
            "base_speed": base_speed.round(3),
            "fatigue_start_hour": fatigue_start_hour,
            "heat_sensitivity": heat_sensitivity.round(3),
            "rain_sensitivity": rain_sensitivity.round(3),
            "belt_skip_probability_when_idle": belt_skip_probability_when_idle.round(3),
        }
    )

    # Planted pattern: seatbelt habit — elevated skip probability for one operator.
    df.loc[df.operator_id == config.SEATBELT_HABIT_OPERATOR_ID, "belt_skip_probability_when_idle"] = 0.55
    return df


def generate_machines(rng: np.random.Generator) -> pd.DataFrame:
    n = config.N_MACHINES
    machine_ids = [f"EXC{i + 1:03d}" for i in range(n)]
    types = rng.choice(MACHINE_TYPES, size=n, p=MACHINE_TYPE_PROBS)
    age_years = rng.uniform(0.5, 12.0, n).round(1)
    # health_drift: gradual efficiency loss per day of the simulation window.
    # Normal machines drift very slowly; the planted machine drifts fast.
    health_drift = rng.uniform(0.0005, 0.0015, n).round(5)

    df = pd.DataFrame(
        {
            "machine_id": machine_ids,
            "type": types,
            "age_years": age_years,
            "health_drift": health_drift,
            "home_zone": [ZONES[i % len(ZONES)] for i in range(n)],
        }
    )
    # Planted pattern: machine degradation — much faster drift for one machine.
    df.loc[df.machine_id == config.DEGRADING_MACHINE_ID, "health_drift"] = 0.0045
    return df


def generate_weather(rng: np.random.Generator) -> pd.DataFrame:
    start = pd.Timestamp(config.SIM_START_DATE)
    hours = config.N_DAYS * 24
    timestamps = pd.date_range(start, periods=hours, freq="h")

    hour_of_day = timestamps.hour.values
    # Smooth daily temperature curve (cool at night, warm mid-afternoon) + noise.
    base_temp = 18 + 10 * np.sin((hour_of_day - 6) / 24 * 2 * np.pi)
    day_drift = 3 * np.sin(np.arange(hours) / (24 * 15) * 2 * np.pi)  # slow seasonal wobble
    noise = rng.normal(0, 1.5, hours)
    temperature = (base_temp + day_drift + noise).round(1)

    condition = rng.choice(WEATHER_CONDITIONS, size=hours, p=WEATHER_PROBS)
    rain_mm = np.where(
        np.isin(condition, ["rain", "storm"]),
        rng.uniform(0.5, 12.0, hours).round(1),
        0.0,
    )
    wind_speed = rng.uniform(2.0, 25.0, hours).round(1)

    return pd.DataFrame(
        {
            "timestamp": timestamps,
            "condition": condition,
            "temperature": temperature,
            "rain_mm": rain_mm,
            "wind_speed": wind_speed,
        }
    )


# ---------------------------------------------------------------------------
# tasks + telemetry (the core simulation loop)
# ---------------------------------------------------------------------------


def _nearest_weather(weather_df: pd.DataFrame, ts: pd.Timestamp) -> pd.Series:
    idx = weather_df["timestamp"].searchsorted(ts, side="right") - 1
    idx = max(0, min(idx, len(weather_df) - 1))
    return weather_df.iloc[idx]


def generate_tasks_and_telemetry(
    rng: np.random.Generator,
    operators_df: pd.DataFrame,
    machines_df: pd.DataFrame,
    weather_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    tasks: list[dict] = []
    telemetry: list[dict] = []

    task_counter = 0
    operator_ids = operators_df["operator_id"].tolist()
    engine_hours_cum = {m: rng.uniform(200, 4000) for m in machines_df["machine_id"]}

    start_date = pd.Timestamp(config.SIM_START_DATE)

    for day in range(config.N_DAYS):
        date = start_date + timedelta(days=day)
        for _, machine in machines_df.iterrows():
            machine_id = machine["machine_id"]
            zone = machine["home_zone"]
            m_lat, m_lon = _zone_coords(zone)

            # Enough tasks to actually fill most of the 10-hour shift (7am-5pm) —
            # with only 1-3 short tasks/day, machines were finishing by ~10am and
            # the afternoon-slowdown pattern (fatigue_start_hour ~1-3pm) never
            # had a chance to trigger. The `clock >= day_end` check below still
            # caps how many of these actually run.
            n_tasks = rng.integers(4, 9)
            clock = date + timedelta(hours=config.SHIFT_START_HOUR)
            day_end = date + timedelta(hours=config.SHIFT_END_HOUR)

            for t in range(n_tasks):
                if clock >= day_end:
                    break

                task_counter += 1
                task_id = f"T{task_counter:03d}"

                if day == 0 and machine_id == config.DEMO_MACHINE_ID and t == 0:
                    operator_id = config.DEMO_OPERATOR_ID
                    task_id = config.DEMO_TASK_ID
                else:
                    operator_id = rng.choice(operator_ids)

                operator = operators_df.loc[operators_df.operator_id == operator_id].iloc[0]

                task_type = rng.choice(TASK_TYPES)
                lo, hi = TASK_VOLUME_RANGE_M3[task_type]
                volume_m3 = round(float(rng.uniform(lo, hi)), 1)
                estimated_buckets = int(np.ceil(volume_m3 / BUCKET_SIZE_M3))

                weather_now = _nearest_weather(weather_df, clock)
                start_hour = clock.hour + clock.minute / 60.0

                # --- pace factors -------------------------------------------------
                skill_factor = SKILL_FACTOR[operator["skill"]]
                rain_penalty = WEATHER_PENALTY[weather_now["condition"]] * (
                    1 + operator["rain_sensitivity"] if weather_now["condition"] in ("rain", "storm") else 1
                )
                heat_excess = max(0.0, weather_now["temperature"] - 30.0)
                heat_penalty = heat_excess * 0.01 * (1 + operator["heat_sensitivity"] * 5)
                fatigue_penalty = 0.0
                if start_hour >= operator["fatigue_start_hour"]:
                    fatigue_penalty = 0.10 + heat_penalty  # afternoon slowdown, worse when hot

                day_fraction = day / max(1, config.N_DAYS - 1)
                machine_health_penalty = machine["health_drift"] * day * 10  # cumulative drift

                total_factor = (
                    (1 + rain_penalty) * (1 + heat_penalty) * (1 + fatigue_penalty) * (1 + machine_health_penalty)
                )
                noise = rng.normal(1.0, 0.03)
                avg_cycle_time_s = max(8.0, (BASE_CYCLE_S / (skill_factor * operator["base_speed"])) * total_factor * noise)

                n_cycles = max(1, estimated_buckets + int(rng.integers(-2, 3)))
                active_time_min = n_cycles * avg_cycle_time_s / 60.0

                is_truck_dependent = task_type in TRUCK_DEPENDENT_TYPES
                idle_legit = rng.uniform(15, 45) if is_truck_dependent else rng.uniform(2, 8)
                idle_extra = rng.uniform(0, 4)
                if operator_id == config.SEATBELT_HABIT_OPERATOR_ID:
                    idle_extra += rng.uniform(8, 20)
                idle_total = idle_legit + idle_extra

                actual_time_min = round(active_time_min + idle_total, 1)

                # Naive dispatcher estimate: knows the task & weather, NOT the
                # specific operator's true speed or fatigue state — this is what
                # makes personalized ETA (Operator Twin) a real modeling problem.
                planner_factor = (1 + rain_penalty) * (1 + heat_penalty * 0.5)
                estimated_time_min = round((estimated_buckets * BASE_CYCLE_S / 60.0) * planner_factor, 1)

                tasks.append(
                    {
                        "task_id": task_id,
                        "task_type": task_type,
                        "zone": zone,
                        "volume_m3": volume_m3,
                        "estimated_buckets": estimated_buckets,
                        "weather": weather_now["condition"],
                        "operator_id": operator_id,
                        "operator_skill": operator["skill"],
                        "machine_id": machine_id,
                        "machine_age": machine["age_years"],
                        "estimated_time_min": estimated_time_min,
                        "actual_time_min": actual_time_min,
                        "start_time": clock,
                        # generation-time flags, used to build task_ground_truth.csv
                        "_is_afternoon_slowdown": start_hour >= operator["fatigue_start_hour"],
                        "_is_legit_idle_dominant": idle_legit >= idle_extra,
                        "_is_degrading_machine_task": machine_id == config.DEGRADING_MACHINE_ID,
                        "_is_inefficient_operator_task": operator_id == config.INEFFICIENT_OPERATOR_ID,
                        "_is_seatbelt_habit_operator_task": operator_id == config.SEATBELT_HABIT_OPERATOR_ID,
                    }
                )

                # --- telemetry for this task ---------------------------------------
                n_intervals = max(1, round(actual_time_min / config.TELEMETRY_INTERVAL_MIN))
                idle_intervals_needed = max(0, round(idle_total / config.TELEMETRY_INTERVAL_MIN))
                idle_start_idx = rng.integers(0, max(1, n_intervals - idle_intervals_needed + 1))
                idle_idx_set = set(range(idle_start_idx, min(n_intervals, idle_start_idx + idle_intervals_needed)))

                unbuckled_state = False
                for i in range(n_intervals):
                    ts = clock + timedelta(minutes=i * config.TELEMETRY_INTERVAL_MIN)
                    is_idle = i in idle_idx_set
                    moving = not is_idle

                    if is_idle:
                        idle_reason = "waiting_for_truck" if is_truck_dependent else "unnecessary"
                    else:
                        idle_reason = None

                    # Seatbelt behavior (planted for one operator; near-zero elsewhere).
                    skip_p = operator["belt_skip_probability_when_idle"]
                    if is_idle and rng.random() < skip_p:
                        unbuckled_state = True
                    elif moving and unbuckled_state and rng.random() < 0.4:
                        pass  # starts moving before re-buckling (the planted violation)
                    elif moving:
                        unbuckled_state = False
                    seatbelt_status = "unbuckled" if unbuckled_state else "buckled"
                    safety_alert = bool(seatbelt_status == "unbuckled" and moving)

                    fuel_rate = 0.6 if moving else 0.15
                    fuel_rate *= 1 + machine_health_penalty * 0.5
                    if operator_id == config.INEFFICIENT_OPERATOR_ID:
                        fuel_rate *= 1.35
                    fuel_rate *= rng.normal(1.0, 0.05)
                    fuel_used_l = round(max(0.0, fuel_rate * config.TELEMETRY_INTERVAL_MIN), 2)

                    cycles_this_interval = (
                        int(round((config.TELEMETRY_INTERVAL_MIN * 60) / avg_cycle_time_s)) if moving else 0
                    )
                    interval_cycle_time = avg_cycle_time_s * rng.normal(1.0, 0.05) if moving else 0.0
                    cycle_time_std = round(avg_cycle_time_s * 0.05, 2)
                    harsh_events = int(rng.poisson(0.05 * (1 + machine_health_penalty))) if moving else 0

                    jitter_lat = rng.normal(0, 0.00003)
                    jitter_lon = rng.normal(0, 0.00003)

                    engine_hours_cum[machine_id] += config.TELEMETRY_INTERVAL_MIN / 60.0

                    telemetry.append(
                        {
                            "timestamp": ts,
                            "machine_id": machine_id,
                            "operator_id": operator_id,
                            "task_id": task_id,
                            "engine_hours": round(engine_hours_cum[machine_id], 2),
                            "fuel_used_l": fuel_used_l,
                            "load_cycles": cycles_this_interval,
                            "avg_cycle_time_s": round(interval_cycle_time, 1),
                            "cycle_time_std": cycle_time_std,
                            "idling_time_min": config.TELEMETRY_INTERVAL_MIN if is_idle else 0,
                            "idle_reason": idle_reason,
                            "seatbelt_status": seatbelt_status,
                            "machine_moving": moving,
                            "harsh_events": harsh_events,
                            "lat": round(m_lat + jitter_lat, 6),
                            "lon": round(m_lon + jitter_lon, 6),
                            "safety_alert": safety_alert,
                        }
                    )

                clock = clock + timedelta(minutes=actual_time_min + rng.uniform(5, 15))

    tasks_df = pd.DataFrame(tasks)
    telemetry_df = pd.DataFrame(telemetry)
    return tasks_df, telemetry_df


# ---------------------------------------------------------------------------
# worker positions + near misses
# ---------------------------------------------------------------------------


def generate_worker_positions_and_near_misses(
    rng: np.random.Generator,
    tasks_df: pd.DataFrame,
    machines_df: pd.DataFrame,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    worker_ids = [f"W{i + 1:03d}" for i in range(config.N_SITE_WORKERS)]
    machine_zone = dict(zip(machines_df["machine_id"], machines_df["home_zone"]))

    positions: list[dict] = []
    near_misses: list[dict] = []
    nm_counter = 0

    for _, task in tasks_df.iterrows():
        m_lat, m_lon = _zone_coords(machine_zone[task["machine_id"]])
        duration_min = task["actual_time_min"]
        n_samples = max(1, int(duration_min // config.WORKER_POSITION_INTERVAL_MIN))
        moving_fraction = 1.0 - min(0.9, 30.0 / max(duration_min, 1))  # rough proxy for "machine is active"

        for i in range(n_samples):
            ts = task["start_time"] + timedelta(minutes=i * config.WORKER_POSITION_INTERVAL_MIN)
            worker_id = worker_ids[(task.name + i) % len(worker_ids)]
            machine_active = rng.random() < moving_fraction

            is_near_miss = machine_active and rng.random() < 0.03
            if is_near_miss:
                lat = m_lat + rng.normal(0, 0.00002)
                lon = m_lon + rng.normal(0, 0.00002)
            else:
                lat = m_lat + rng.normal(0, 0.0004)
                lon = m_lon + rng.normal(0, 0.0004)

            positions.append({"timestamp": ts, "worker_id": worker_id, "lat": round(lat, 6), "lon": round(lon, 6)})

            if is_near_miss:
                dist = distance_m(lat, lon, m_lat, m_lon)
                if dist <= config.SWING_ZONE_RADIUS_M:
                    nm_counter += 1
                    near_misses.append(
                        {
                            "near_miss_id": f"NM{nm_counter:04d}",
                            "timestamp": ts,
                            "worker_id": worker_id,
                            "machine_id": task["machine_id"],
                            "task_id": task["task_id"],
                            "distance_m": round(dist, 2),
                        }
                    )

    return pd.DataFrame(positions), pd.DataFrame(near_misses)


# ---------------------------------------------------------------------------
# incidents + training events
# ---------------------------------------------------------------------------


def generate_incidents(
    rng: np.random.Generator,
    telemetry_df: pd.DataFrame,
    near_misses_df: pd.DataFrame,
) -> pd.DataFrame:
    incidents: list[dict] = []
    counter = 0

    alert_rows = telemetry_df[telemetry_df["safety_alert"]]
    reported = alert_rows.sample(frac=0.2, random_state=int(rng.integers(0, 1_000_000))) if len(alert_rows) else alert_rows
    for _, row in reported.iterrows():
        counter += 1
        incidents.append(
            {
                "incident_id": f"INC{counter:04d}",
                "timestamp": row["timestamp"],
                "operator_id": row["operator_id"],
                "machine_id": row["machine_id"],
                "task_id": row["task_id"],
                "incident_type": "seatbelt",
                "severity": "medium",
                "description": "Seatbelt not fastened while machine in motion.",
            }
        )

    reported_nm = (
        near_misses_df.sample(frac=0.3, random_state=int(rng.integers(0, 1_000_000)))
        if len(near_misses_df)
        else near_misses_df
    )
    for _, row in reported_nm.iterrows():
        counter += 1
        incidents.append(
            {
                "incident_id": f"INC{counter:04d}",
                "timestamp": row["timestamp"],
                "operator_id": None,
                "machine_id": row["machine_id"],
                "task_id": row["task_id"],
                "incident_type": "near_miss",
                "severity": "high",
                "description": f"Worker {row['worker_id']} entered swing zone ({row['distance_m']}m).",
            }
        )

    return pd.DataFrame(incidents)


def generate_training_events(rng: np.random.Generator, tasks_df: pd.DataFrame) -> pd.DataFrame:
    events: list[dict] = []
    counter = 0

    habit_tasks = tasks_df[tasks_df["_is_seatbelt_habit_operator_task"]].sort_values("start_time")
    checkpoints = habit_tasks.iloc[:: max(1, len(habit_tasks) // 5)] if len(habit_tasks) else habit_tasks
    for i, (_, row) in enumerate(checkpoints.iterrows()):
        counter += 1
        completed = bool(rng.random() < 0.7)
        events.append(
            {
                "event_id": f"TR{counter:04d}",
                "operator_id": row["operator_id"],
                "timestamp": row["start_time"] + timedelta(hours=1),
                "module": "seatbelt_awareness",
                "trigger": "just_in_time",
                "completed": completed,
                # deterministic mild improvement trend over successive checkpoints
                "score": round(min(98.0, 55.0 + i * 6 + rng.uniform(-3, 3)), 1) if completed else None,
            }
        )

    return pd.DataFrame(events)


# ---------------------------------------------------------------------------
# ground truth
# ---------------------------------------------------------------------------


def generate_ground_truth_labels() -> pd.DataFrame:
    start = pd.Timestamp(config.SIM_START_DATE)
    end = start + timedelta(days=config.N_DAYS - 1)
    rows = [
        {
            "label_id": "GT001",
            "pattern_type": "seatbelt_habit",
            "entity_type": "operator",
            "entity_id": config.SEATBELT_HABIT_OPERATOR_ID,
            "description": "Unbuckles during long idle waits; sometimes starts moving before re-buckling.",
            "start_date": start,
            "end_date": end,
        },
        {
            "label_id": "GT002",
            "pattern_type": "afternoon_slowdown",
            "entity_type": "global",
            "entity_id": "all_operators",
            "description": "Pace drops after each operator's fatigue_start_hour (~1-3pm), worse in heat.",
            "start_date": start,
            "end_date": end,
        },
        {
            "label_id": "GT003",
            "pattern_type": "machine_degradation",
            "entity_type": "machine",
            "entity_id": config.DEGRADING_MACHINE_ID,
            "description": "Cycle time and fuel use rise across the window for every operator on this machine.",
            "start_date": start,
            "end_date": end,
        },
        {
            "label_id": "GT004",
            "pattern_type": "operator_inefficiency",
            "entity_type": "operator",
            "entity_id": config.INEFFICIENT_OPERATOR_ID,
            "description": "Consistently higher fuel use per active minute across multiple machines.",
            "start_date": start,
            "end_date": end,
        },
        {
            "label_id": "GT005",
            "pattern_type": "legitimate_idle",
            "entity_type": "task_type",
            "entity_id": ",".join(sorted(TRUCK_DEPENDENT_TYPES)),
            "description": "Idle time while waiting for trucks; must not be attributed to the operator as a fault.",
            "start_date": start,
            "end_date": end,
        },
        {
            "label_id": "GT006",
            "pattern_type": "proximity_near_miss",
            "entity_type": "site",
            "entity_id": "all_machines",
            "description": "Workers repeatedly enter a machine's swing-zone area (see near_misses.csv).",
            "start_date": start,
            "end_date": end,
        },
    ]
    return pd.DataFrame(rows)


def build_task_ground_truth(tasks_df: pd.DataFrame, near_misses_df: pd.DataFrame) -> pd.DataFrame:
    tasks_with_nm = set(near_misses_df["task_id"]) if len(near_misses_df) else set()
    out = tasks_df[["task_id"]].copy()
    out["is_afternoon_slowdown"] = tasks_df["_is_afternoon_slowdown"]
    out["is_legitimate_idle_dominant"] = tasks_df["_is_legit_idle_dominant"]
    out["is_degrading_machine_task"] = tasks_df["_is_degrading_machine_task"]
    out["is_inefficient_operator_task"] = tasks_df["_is_inefficient_operator_task"]
    out["is_seatbelt_habit_operator_task"] = tasks_df["_is_seatbelt_habit_operator_task"]
    out["has_near_miss"] = tasks_df["task_id"].isin(tasks_with_nm)
    return out


# ---------------------------------------------------------------------------
# orchestration
# ---------------------------------------------------------------------------


def generate_all(seed: int = config.SEED) -> dict[str, pd.DataFrame]:
    """Generate every table deterministically and return them as a dict."""
    rng = np.random.default_rng(seed)

    operators_df = generate_operators(rng)
    machines_df = generate_machines(rng)
    weather_df = generate_weather(rng)
    tasks_df, telemetry_df = generate_tasks_and_telemetry(rng, operators_df, machines_df, weather_df)
    worker_positions_df, near_misses_df = generate_worker_positions_and_near_misses(rng, tasks_df, machines_df)
    incidents_df = generate_incidents(rng, telemetry_df, near_misses_df)
    training_events_df = generate_training_events(rng, tasks_df)
    ground_truth_labels_df = generate_ground_truth_labels()
    task_ground_truth_df = build_task_ground_truth(tasks_df, near_misses_df)

    # Drop generation-time helper columns before returning the public tasks table.
    tasks_public_df = tasks_df.drop(columns=[c for c in tasks_df.columns if c.startswith("_")])
    machines_public_df = machines_df.drop(columns=["home_zone"])

    return {
        "operators": operators_df,
        "machines": machines_public_df,
        "weather": weather_df,
        "tasks": tasks_public_df,
        "telemetry": telemetry_df,
        "worker_positions": worker_positions_df,
        "near_misses": near_misses_df,
        "incidents": incidents_df,
        "training_events": training_events_df,
        "ground_truth_labels": ground_truth_labels_df,
        "task_ground_truth": task_ground_truth_df,
    }


def write_all(tables: dict[str, pd.DataFrame]) -> dict[str, str]:
    """Write every generated table to `data/synthetic/` or `data/ground_truth/`."""
    written = {}
    ground_truth_tables = {"ground_truth_labels", "task_ground_truth"}
    for name, df in tables.items():
        base_dir = config.GROUND_TRUTH_DIR if name in ground_truth_tables else config.SYNTHETIC_DIR
        path = write_csv(df, base_dir / f"{name}.csv")
        written[name] = str(path)
    return written


def main() -> None:
    tables = generate_all()
    written = write_all(tables)
    print("Synthetic data generation complete:")
    for name, df in tables.items():
        print(f"  {name:<20} {len(df):>7} rows  -> {written[name]}")


if __name__ == "__main__":
    main()
