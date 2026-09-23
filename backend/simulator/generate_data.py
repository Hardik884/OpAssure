"""Deterministic synthetic data generator (handover §6-8, CLAUDE.md §6).

`generate_dataset()` returns plain row dicts keyed by table name; `simulator.seed`
writes them to PostgreSQL. Same SEED -> byte-identical dataset on every run.

What is generated
-----------------
* 20 operators (6 Beginner / 8 Intermediate / 6 Expert) with persistent traits.
* 8 machines (5 excavators, 3 loaders) of different ages with a health drift.
* Hourly weather for 60 days (warming trend, two heat waves, showers/rainy days).
* Days 0-58 are history: every half-shift each machine gets an operator, who works
  tasks back to back. Each task is simulated minute by minute (cycle time from
  machine, operator, weather and fatigue; truck waits; avoidable idle; seatbelt
  behaviour; harsh events) and sampled into telemetry every 5-15 minutes, plus an
  extra sample whenever the seatbelt state changes.
* Day 59 is demo day ("today"): tasks are scheduled only, except the scripted demo
  task T001 (see scenarios.py).
* Worker positions every 10 minutes during shifts; 1-minute tracks for near misses.
* Incidents, near misses, training events, ground-truth labels.

Planted problems (all labelled in ground_truth_labels)
------------------------------------------------------
seatbelt_pattern       OP1001 unbuckles in long truck waits, often moves before re-buckling
afternoon_slowdown     OP1001 & OP1012 slow down after 14:00, much more on hot days
machine_degradation    EXC003 fuel and cycle time rise ~0.6%/day for every operator
operator_inefficiency  OP1015 burns 40% extra fuel on whichever machine they use
legitimate_idle        10 truck-shortage days create 10-25 min truck waits (not operator fault)
proximity_near_miss    worker W04 repeatedly walks into EXC001's swing zone
"""

import math
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta

import numpy as np
from faker import Faker

from app.services.safety_service import evaluate_telemetry, proximity_severity, relative_direction
from simulator import scenarios as demo

SEED = 20250501
START_DATE = date(2025, 5, 1)
NUM_DAYS = 60
DEMO_DAY_INDEX = NUM_DAYS - 1
DEMO_DATE = START_DATE + timedelta(days=DEMO_DAY_INDEX)

# Site geometry. Positions are handled in metres (east, north) from the site origin.
SITE_LAT, SITE_LON = 40.6936, -89.5890
ZONES = {"A": (0.0, 0.0), "B": (400.0, 0.0), "C": (0.0, 400.0), "D": (400.0, 400.0), "E": (-400.0, 200.0)}
DEMO_SPOT = (5.0, -8.0)  # T001 dig position in zone A

HALF_SHIFTS = ((7 * 60, 12 * 60), (12 * 60 + 30, 17 * 60))  # minutes since midnight
WORKER_GRID_MIN = 10
NUM_WORKERS = 12

SKILLS = (
    "Intermediate", "Expert", "Beginner", "Intermediate", "Expert",
    "Beginner", "Intermediate", "Beginner", "Expert", "Intermediate",
    "Beginner", "Intermediate", "Expert", "Intermediate", "Intermediate",
    "Beginner", "Expert", "Intermediate", "Beginner", "Expert",
)  # OP1001..OP1020
SKILL_PARAMS = {
    "Beginner": {"speed": 0.85, "cycle_cv": 0.18, "fuel": 1.08, "avoidable_idle_per_min": 1 / 45, "harsh_per_hour": 0.40},
    "Intermediate": {"speed": 1.00, "cycle_cv": 0.12, "fuel": 1.00, "avoidable_idle_per_min": 1 / 80, "harsh_per_hour": 0.15},
    "Expert": {"speed": 1.12, "cycle_cv": 0.07, "fuel": 0.95, "avoidable_idle_per_min": 1 / 150, "harsh_per_hour": 0.05},
}

MACHINE_SPECS = (  # machine_id, type, model, age_years
    ("EXC001", "excavator", "CAT 320", 2),
    ("EXC002", "excavator", "CAT 320", 6),
    ("EXC003", "excavator", "CAT 336", 9),
    ("EXC004", "excavator", "CAT 330", 4),
    ("EXC005", "excavator", "CAT 336", 12),
    ("LDR001", "loader", "CAT 950 GC", 3),
    ("LDR002", "loader", "CAT 966", 8),
    ("LDR003", "loader", "CAT 950 GC", 5),
)
MACHINE_TYPES = {
    "excavator": {"cycle_s": 22.0, "bucket_m3": 1.5, "fuel_lph": 17.0,
                  "task_types": ("excavation", "trenching", "truck_loading", "backfilling")},
    "loader": {"cycle_s": 32.0, "bucket_m3": 3.0, "fuel_lph": 20.0,
               "task_types": ("truck_loading", "stockpiling", "site_cleanup")},
}
TASK_VOLUME_M3 = {
    "excavation": (120, 320), "trenching": (60, 180), "truck_loading": (150, 360),
    "backfilling": (100, 250), "stockpiling": (200, 450), "site_cleanup": (100, 300),
}
PLAN_OVERHEAD = 1.15  # naive plan: standard cycle time + 15%
IDLE_FUEL_LPH = 3.0
TRUCK_WAIT_HAZARD = 1 / 18  # per working minute on truck_loading tasks

# ---- planted problems ----
SEATBELT_HABIT_OPERATOR = "OP1001"
AFTERNOON_SLOWDOWN_OPERATORS = ("OP1001", "OP1012")
DEGRADING_MACHINE = "EXC003"
DEGRADING_DRIFT = 0.006
DEGRADATION_DETECTABLE_FROM_DAY = 20  # before this the drift is labelled but too small to expect
INEFFICIENT_OPERATOR = "OP1015"
INEFFICIENT_FUEL_FACTOR = 1.40
NUM_TRUCK_DELAY_DAYS = 10
LONG_TRUCK_WAIT_MIN = 8
NEAR_MISS_WORKER = demo.DEMO_WORKER_ID
NEAR_MISS_MACHINE = demo.DEMO_MACHINE_ID
NUM_NEAR_MISSES = 12
NUM_HARSH_INCIDENTS = 10
HEAT_WAVE_DAYS = tuple(range(20, 24)) + tuple(range(44, 48))

# operator_id, day, trigger, clip_id, completed. Completed training changes later behaviour.
TRAINING_PLAN = (
    ("OP1003", 30, "avoidable_idle", "CLIP_IDLE_01", True),
    ("OP1008", 30, "avoidable_idle", "CLIP_IDLE_01", True),
    ("OP1016", 35, "harsh_events", "CLIP_SMOOTH_01", True),
    ("OP1011", 50, "avoidable_idle", "CLIP_IDLE_01", False),
)
TRAINING_WINDOW_DAYS = 14


def to_latlon(east_m: float, north_m: float) -> tuple[float, float]:
    lat = SITE_LAT + north_m / 111_320.0
    lon = SITE_LON + east_m / (111_320.0 * math.cos(math.radians(SITE_LAT)))
    return round(float(lat), 6), round(float(lon), 6)


def _day_start(day: int) -> datetime:
    return datetime.combine(START_DATE + timedelta(days=day), time(0, 0))


class _Generator:
    def __init__(self, seed: int):
        self.seed = seed
        self.rng = np.random.default_rng(seed)
        self.out: dict[str, list[dict]] = defaultdict(list)
        self.weather_by_hour: dict[datetime, dict] = {}
        self.ops: dict[str, dict] = {}  # row fields + hidden simulation traits
        self.machines: dict[str, dict] = {}
        self.engine_hours: dict[str, float] = {}
        self.telemetry_by_task: dict[int, list[dict]] = defaultdict(list)
        # (operator_id, day) -> engine minutes / avoidable idle minutes / harsh events
        self.op_day_stats: dict[tuple[str, int], Counter] = defaultdict(Counter)
        self.training_day = {
            (op, trig): day for op, day, trig, _, done in TRAINING_PLAN if done
        }

    # ------------------------------------------------------------------ entities
    def gen_operators(self) -> None:
        fake = Faker("en_US")
        fake.seed_instance(self.seed)
        for i, skill in enumerate(SKILLS):
            op_id = f"OP{1001 + i}"
            p = SKILL_PARAMS[skill]
            row = {
                "operator_id": op_id,
                "name": fake.name(),
                "skill": skill,
                "base_speed": round(float(p["speed"] + self.rng.normal(0, 0.04)), 3),
                "fatigue_start_hour": int(self.rng.choice([15, 16, 17])),
                "heat_sensitivity": round(float(self.rng.uniform(0.1, 0.5)), 3),
                "rain_sensitivity": round(float(self.rng.uniform(0.1, 0.5)), 3),
                "belt_skip_probability_when_idle": round(float(self.rng.uniform(0.0, 0.04)), 3),
            }
            hidden = {
                "cycle_cv": p["cycle_cv"],
                "fuel_factor": p["fuel"],
                "avoidable_idle_per_min": p["avoidable_idle_per_min"],
                "harsh_per_hour": p["harsh_per_hour"],
                "fatigue_rate": 0.015,  # fractional slowdown per hour past fatigue_start_hour
                "fatigue_heat_amp": 0.0,
                "p_move_unbelted": 0.15,
            }
            if op_id == SEATBELT_HABIT_OPERATOR:
                row["belt_skip_probability_when_idle"] = 0.65
                hidden["p_move_unbelted"] = 0.55
            if op_id in AFTERNOON_SLOWDOWN_OPERATORS:
                row["fatigue_start_hour"] = 14
                row["heat_sensitivity"] = 0.85
                hidden["fatigue_rate"] = 0.06
                hidden["fatigue_heat_amp"] = 1.5
            if op_id == INEFFICIENT_OPERATOR:
                hidden["fuel_factor"] *= INEFFICIENT_FUEL_FACTOR
            self.out["operators"].append(row)
            self.ops[op_id] = {**row, **hidden}

    def gen_machines(self) -> None:
        for machine_id, mtype, model, age in MACHINE_SPECS:
            drift = DEGRADING_DRIFT if machine_id == DEGRADING_MACHINE else 0.0002 + 0.00004 * age
            row = {"machine_id": machine_id, "type": mtype, "model": model,
                   "age_years": age, "health_drift": round(drift, 5)}
            self.out["machines"].append(row)
            self.machines[machine_id] = row
            self.engine_hours[machine_id] = round(age * 1400 + float(self.rng.uniform(0, 300)), 2)

    def gen_weather(self) -> None:
        for day in range(NUM_DAYS):
            mean = 17 + 7 * day / (NUM_DAYS - 1) + float(self.rng.normal(0, 2.0))
            if day in HEAT_WAVE_DAYS:
                mean += 6
            r = self.rng.random()
            rain_by_hour: dict[int, float] = {}
            if 0.55 <= r < 0.85:  # showers
                start, dur = int(self.rng.integers(8, 17)), int(self.rng.integers(1, 4))
                for h in range(start, min(start + dur, 24)):
                    rain_by_hour[h] = float(self.rng.gamma(1.5, 0.8))
            elif r >= 0.85:  # rainy day
                start, dur = int(self.rng.integers(0, 12)), int(self.rng.integers(6, 14))
                for h in range(start, min(start + dur, 24)):
                    rain_by_hour[h] = float(self.rng.gamma(2.0, 1.5))
            overcast = r >= 0.55 or self.rng.random() < 0.3
            for h in range(24):
                rain = round(rain_by_hour.get(h, 0.0), 1)
                temp = mean + 6 * math.sin(2 * math.pi * (h - 9) / 24) + float(self.rng.normal(0, 0.4))
                wind = float(self.rng.gamma(2.0, 5.0))
                if rain > 0:
                    temp -= 2
                    wind += 8
                if rain >= 4:
                    cond = "heavy_rain"
                elif rain > 0:
                    cond = "rain"
                else:
                    cond = "cloudy" if overcast else "clear"
                if day == DEMO_DAY_INDEX and h in demo.DEMO_WEATHER:
                    cond, temp, rain, wind = demo.DEMO_WEATHER[h]
                row = {"timestamp": _day_start(day) + timedelta(hours=h), "condition": cond,
                       "temperature": round(temp, 1), "rain_mm": rain, "wind_speed": round(wind, 1)}
                self.out["weather"].append(row)
                self.weather_by_hour[row["timestamp"]] = row

    def weather_at(self, ts: datetime) -> dict:
        return self.weather_by_hour[ts.replace(minute=0, second=0, microsecond=0)]

    # ------------------------------------------------------------------ tasks
    def _new_task(self, day: int, start_min: int, op_id: str, machine_id: str) -> dict:
        m = self.machines[machine_id]
        mt = MACHINE_TYPES[m["type"]]
        task_type = str(self.rng.choice(mt["task_types"]))
        lo, hi = TASK_VOLUME_M3[task_type]
        volume = float(round(self.rng.uniform(lo, hi) / 5) * 5)
        buckets = math.ceil(volume / mt["bucket_m3"])
        start = _day_start(day) + timedelta(minutes=start_min)
        return {
            "task_id": None,  # assigned chronologically in assign_task_ids()
            "task_type": task_type,
            "zone": str(self.rng.choice(list(ZONES))),
            "volume_m3": volume,
            "estimated_buckets": buckets,
            "weather": self.weather_at(start)["condition"],
            "operator_id": op_id,
            "operator_skill": self.ops[op_id]["skill"],
            "machine_id": machine_id,
            "machine_age": m["age_years"],
            "estimated_time_min": float(round(buckets * mt["cycle_s"] / 60 * PLAN_OVERHEAD)),
            "actual_time_min": None,
            "start_time": start,
            "status": "scheduled",
        }

    def _simulate_task(self, day: int, task: dict, truck_delay_day: bool) -> tuple[list, list, list]:
        """Minute-by-minute simulation. Returns (states, events, idle_episodes)."""
        rng = self.rng
        op = self.ops[task["operator_id"]]
        m = self.machines[task["machine_id"]]
        mt = MACHINE_TYPES[m["type"]]
        drift = m["health_drift"] * day
        avoid_hazard = op["avoidable_idle_per_min"]
        if day >= self.training_day.get((op["operator_id"], "avoidable_idle"), NUM_DAYS):
            avoid_hazard *= 0.4
        harsh_p = op["harsh_per_hour"] / 60
        if day >= self.training_day.get((op["operator_id"], "harsh_events"), NUM_DAYS):
            harsh_p *= 0.5

        states: list[dict] = []
        events: list[tuple[int, str]] = []
        episodes: list[tuple[int, int, str]] = []
        cycles_left = float(task["estimated_buckets"])
        idle_left, idle_reason, ep_pos = 0, None, 0
        belted, unbelted_moves_left, move_event_pending = True, 0, False
        minute = 0
        while cycles_left > 0:
            ts = task["start_time"] + timedelta(minutes=minute)
            if idle_left == 0 and minute > 0:
                if task["task_type"] == "truck_loading" and rng.random() < TRUCK_WAIT_HAZARD:
                    dur = int(rng.integers(10, 26)) if truck_delay_day else int(rng.integers(2, 8))
                    idle_left, idle_reason, ep_pos = dur, "truck_wait", 0
                    episodes.append((minute, dur, "truck_wait"))
                elif rng.random() < avoid_hazard:
                    dur = int(rng.integers(3, 11))
                    idle_left, idle_reason, ep_pos = dur, "avoidable", 0
                    episodes.append((minute, dur, "avoidable"))

            if idle_left > 0:
                if (idle_reason == "truck_wait" and ep_pos == 2 and episodes[-1][1] >= 5 and belted
                        and rng.random() < op["belt_skip_probability_when_idle"]):
                    belted = False
                    events.append((minute, "unbuckle"))
                    if rng.random() < op["p_move_unbelted"]:
                        unbelted_moves_left = int(rng.integers(1, 4))
                        move_event_pending = True
                states.append({"working": False, "cycle_s": None, "cycles": 0.0,
                               "fuel_l": IDLE_FUEL_LPH / 60, "idle_reason": idle_reason,
                               "belted": belted, "harsh": 0})
                idle_left -= 1
                ep_pos += 1
                if idle_left == 0 and not belted and unbelted_moves_left == 0:
                    belted = True  # re-buckled before moving off
                minute += 1
                continue

            wx = self.weather_at(ts)
            cycle = mt["cycle_s"] / op["base_speed"] * (1 + 0.5 * drift)
            cycle *= 1 + 0.3 * op["rain_sensitivity"] * min(wx["rain_mm"] / 4, 1.0)
            cycle *= 1 + 0.15 * op["heat_sensitivity"] * max(0.0, wx["temperature"] - 27) / 8
            past_fatigue = ts.hour + ts.minute / 60 - op["fatigue_start_hour"]
            if past_fatigue > 0:
                heat = op["fatigue_heat_amp"] * max(0.0, wx["temperature"] - 26) / 8
                cycle *= 1 + op["fatigue_rate"] * past_fatigue * (1 + heat)
            cycle *= float(rng.lognormal(0, 0.05))
            fuel = mt["fuel_lph"] / 60 * (1 + drift) * op["fuel_factor"] * float(rng.lognormal(0, 0.04))
            harsh = int(rng.random() < harsh_p)
            if not belted and move_event_pending:
                events.append((minute, "move_unbelted"))
                move_event_pending = False
            cycles = 60.0 / cycle
            states.append({"working": True, "cycle_s": cycle, "cycles": cycles, "fuel_l": fuel,
                           "idle_reason": None, "belted": belted, "harsh": harsh})
            cycles_left -= cycles
            if not belted:
                unbelted_moves_left -= 1
                if unbelted_moves_left <= 0:
                    belted = True
            minute += 1
        return states, events, episodes

    def _sample_minutes(self, n: int, forced: list[int]) -> list[int]:
        marks = set(forced)
        s = int(self.rng.integers(5, 16))
        while s < n:
            marks.add(s)
            s += int(self.rng.integers(5, 16))
        marks.add(n)
        return sorted(x for x in marks if 1 <= x <= n)

    def _telemetry_rows(self, rng, task: dict, states: list[dict], samples: list[int],
                        spot: tuple[float, float], cycle_cv: float) -> list[dict]:
        cum = np.concatenate([[0.0], np.cumsum([s["cycles"] for s in states])])
        engine_start = self.engine_hours[task["machine_id"]]
        rows, prev = [], 0
        for b in samples:
            seg, cur = states[prev:b], states[b - 1]
            work = [s["cycle_s"] for s in seg if s["working"]]
            idle = [s["idle_reason"] for s in seg if not s["working"]]
            reason = Counter(idle).most_common(1)[0][0] if idle else None
            avg = round(float(np.mean(work)), 2) if work else None
            std = round(avg * cycle_cv * float(rng.lognormal(0, 0.15)), 2) if work else None
            belt = "fastened" if cur["belted"] else "unfastened"
            alert = evaluate_telemetry(seatbelt_status=belt, machine_moving=cur["working"],
                                       idling_time_min=float(len(idle)), idle_reason=reason)
            east = spot[0] + float(rng.normal(0, 2.0))
            north = spot[1] + float(rng.normal(0, 2.0))
            lat, lon = to_latlon(east, north)
            rows.append({
                "timestamp": task["start_time"] + timedelta(minutes=b),
                "machine_id": task["machine_id"],
                "operator_id": task["operator_id"],
                "_task": task,
                "engine_hours": round(engine_start + b / 60, 2),
                "fuel_used_l": round(sum(s["fuel_l"] for s in seg), 2),
                "load_cycles": int(round(cum[b]) - round(cum[prev])),
                "avg_cycle_time_s": avg,
                "cycle_time_std": std,
                "idling_time_min": float(len(idle)),
                "idle_reason": reason,
                "seatbelt_status": belt,
                "machine_moving": bool(cur["working"]),
                "harsh_events": int(sum(s["harsh"] for s in seg)),
                "lat": lat,
                "lon": lon,
                "safety_alert": alert.type if alert else None,
            })
            prev = b
        self.engine_hours[task["machine_id"]] = round(engine_start + len(states) / 60, 2)
        return rows

    def _label(self, problem: str, ts: datetime, description: str, *, operator_id=None,
               machine_id=None, worker_id=None, task=None, expected=True) -> None:
        self.out["ground_truth_labels"].append({
            "problem": problem, "operator_id": operator_id, "machine_id": machine_id,
            "worker_id": worker_id, "_task": task, "timestamp": ts,
            "expected_detection": expected, "description": description,
        })

    def _run_history_task(self, day: int, task: dict, truck_delay_day: bool) -> None:
        op_id, machine_id = task["operator_id"], task["machine_id"]
        states, events, episodes = self._simulate_task(day, task, truck_delay_day)
        task["actual_time_min"] = float(len(states))
        task["status"] = "completed"
        forced = [minute + 1 for minute, _ in events]
        samples = self._sample_minutes(len(states), forced)
        cx, cy = ZONES[task["zone"]]
        spot = (cx + float(self.rng.uniform(-20, 20)), cy + float(self.rng.uniform(-20, 20)))
        task["_spot"] = spot
        rows = self._telemetry_rows(self.rng, task, states, samples, spot, self.ops[op_id]["cycle_cv"])
        self.out["telemetry"].extend(rows)
        self.telemetry_by_task[id(task)] = rows

        stats = self.op_day_stats[(op_id, day)]
        stats["engine_min"] += len(states)
        stats["avoidable_idle_min"] += sum(1 for s in states if s["idle_reason"] == "avoidable")
        stats["harsh"] += sum(s["harsh"] for s in states)

        start = task["start_time"]
        if op_id == SEATBELT_HABIT_OPERATOR:
            for minute, kind in events:
                desc = ("Unbuckled during a long truck wait" if kind == "unbuckle"
                        else "Started moving before re-buckling seatbelt")
                self._label("seatbelt_pattern", start + timedelta(minutes=minute), desc,
                            operator_id=op_id, machine_id=machine_id, task=task)
        for ep_start, dur, reason in episodes:
            if reason == "truck_wait" and dur >= LONG_TRUCK_WAIT_MIN:
                self._label("legitimate_idle", start + timedelta(minutes=ep_start),
                            f"{dur} min truck wait (truck shortage day) - not an operator fault",
                            operator_id=op_id, machine_id=machine_id, task=task)
        if op_id == INEFFICIENT_OPERATOR:
            self._label("operator_inefficiency", start,
                        f"Operator burns {INEFFICIENT_FUEL_FACTOR - 1:.0%} extra fuel on any machine",
                        operator_id=op_id, machine_id=machine_id, task=task)

    def gen_history_and_schedule(self) -> None:
        op_ids = [row["operator_id"] for row in self.out["operators"]]
        machine_ids = [m[0] for m in MACHINE_SPECS]
        delay_days = sorted(int(d) for d in self.rng.choice(DEMO_DAY_INDEX, NUM_TRUCK_DELAY_DAYS, replace=False))
        self.truck_delay_days = delay_days
        self.demo_task: dict | None = None

        for day in range(NUM_DAYS):
            is_demo_day = day == DEMO_DAY_INDEX
            used_degrading = False
            for half, (h_start, h_end) in enumerate(HALF_SHIFTS):
                crew = [op_ids[int(i)] for i in self.rng.permutation(len(op_ids))[: len(machine_ids)]]
                if is_demo_day and half == 0:
                    if demo.DEMO_OPERATOR_ID in crew:
                        crew.remove(demo.DEMO_OPERATOR_ID)
                    else:
                        crew.pop()
                    crew.insert(machine_ids.index(demo.DEMO_MACHINE_ID), demo.DEMO_OPERATOR_ID)
                for machine_id, op_id in zip(machine_ids, crew):
                    t = h_start + int(self.rng.integers(0, 16))
                    if is_demo_day and half == 0 and machine_id == demo.DEMO_MACHINE_ID:
                        self.demo_task = self._make_demo_task()
                        t = demo.DEMO_TASK_START.hour * 60 + demo.DEMO_TASK_START.minute
                        t += int(demo.DEMO_TASK["estimated_time_min"]) + 10
                    worked_afternoon = False
                    while t <= h_end - 30:
                        task = self._new_task(day, t, op_id, machine_id)
                        self.out["tasks"].append(task)
                        if is_demo_day:
                            t += int(task["estimated_time_min"]) + int(self.rng.integers(5, 16))
                            continue
                        self._run_history_task(day, task, day in delay_days)
                        t += int(task["actual_time_min"]) + int(self.rng.integers(5, 16))
                        worked_afternoon = worked_afternoon or half == 1
                        used_degrading = used_degrading or machine_id == DEGRADING_MACHINE
                    if worked_afternoon and op_id in AFTERNOON_SLOWDOWN_OPERATORS:
                        op = self.ops[op_id]
                        ts = _day_start(day) + timedelta(hours=op["fatigue_start_hour"])
                        peak = max(self.weather_at(ts + timedelta(hours=h))["temperature"] for h in range(4))
                        hot = " (hot day - stronger)" if peak >= 28 else ""
                        self._label("afternoon_slowdown", ts,
                                    f"Pace drops after {op['fatigue_start_hour']}:00; afternoon peak {peak} C{hot}",
                                    operator_id=op_id)
            if used_degrading:
                loss = self.machines[DEGRADING_MACHINE]["health_drift"] * day
                self._label("machine_degradation", _day_start(day) + timedelta(hours=7),
                            f"Fuel per hour +{loss:.1%}, cycle time +{loss / 2:.1%} vs new, for every operator",
                            machine_id=DEGRADING_MACHINE, expected=day >= DEGRADATION_DETECTABLE_FROM_DAY)

    # ------------------------------------------------------------------ demo task T001
    def _make_demo_task(self) -> dict:
        start = datetime.combine(DEMO_DATE, demo.DEMO_TASK_START)
        m = self.machines[demo.DEMO_MACHINE_ID]
        task = {
            "task_id": demo.DEMO_TASK_ID,
            **demo.DEMO_TASK,
            "weather": self.weather_at(start)["condition"],
            "operator_id": demo.DEMO_OPERATOR_ID,
            "operator_skill": self.ops[demo.DEMO_OPERATOR_ID]["skill"],
            "machine_id": demo.DEMO_MACHINE_ID,
            "machine_age": m["age_years"],
            "actual_time_min": None,  # the demo plays it out live
            "start_time": start,
            "status": "scheduled",
            "_spot": DEMO_SPOT,
        }
        self.out["tasks"].append(task)
        return task

    def gen_demo_telemetry(self) -> None:
        """Scripted replay telemetry for T001 (1-minute rows, separate RNG)."""
        task = self.demo_task
        demo_rng = np.random.default_rng(self.seed + 1)
        states = demo.demo_minute_states()
        rows = self._telemetry_rows(demo_rng, task, states, list(range(1, len(states) + 1)),
                                    DEMO_SPOT, self.ops[demo.DEMO_OPERATOR_ID]["cycle_cv"])
        self.out["telemetry"].extend(rows)
        self.telemetry_by_task[id(task)] = rows
        start = task["start_time"]
        common = {"operator_id": demo.DEMO_OPERATOR_ID, "machine_id": demo.DEMO_MACHINE_ID, "task": task}
        self._label("legitimate_idle", start + timedelta(minutes=demo.TRUCK_WAIT_MINUTES.start),
                    f"Demo: {len(demo.TRUCK_WAIT_MINUTES)} min truck wait - not an operator fault", **common)
        self._label("seatbelt_pattern", start + timedelta(minutes=demo.UNBUCKLE_MINUTE),
                    "Demo: unbuckled during truck wait", **common)
        self._label("seatbelt_pattern", start + timedelta(minutes=demo.MOVE_UNBELTED_MINUTES.start),
                    "Demo: started moving before re-buckling seatbelt", **common)
        closest = min(demo.WORKER_APPROACH_DISTANCES_M)
        at = demo.WORKER_APPROACH_START_MINUTE + demo.WORKER_APPROACH_DISTANCES_M.index(closest)
        self._label("proximity_near_miss", start + timedelta(minutes=at),
                    f"Demo: {NEAR_MISS_WORKER} enters right-side swing zone ({closest:.0f} m)",
                    worker_id=NEAR_MISS_WORKER, **common)

    def assign_task_ids(self) -> None:
        others = sorted((t for t in self.out["tasks"] if t["task_id"] is None),
                        key=lambda t: (t["start_time"], t["machine_id"]))
        for n, task in enumerate(others, start=2):  # T001 is reserved for the demo task
            task["task_id"] = f"T{n:03d}"

    # ------------------------------------------------------------------ workers / safety events
    def gen_near_misses_and_workers(self) -> None:
        # Worker tracks that override the 10-minute baseline: worker_id -> [(minute_ts, east, north)]
        tracks: dict[str, list[tuple[datetime, float, float]]] = defaultdict(list)

        candidates = [t for t in self.out["tasks"]
                      if t["machine_id"] == NEAR_MISS_MACHINE and t["status"] == "completed"
                      and t["actual_time_min"] >= 20]
        picks = sorted(int(i) for i in self.rng.choice(len(candidates), NUM_NEAR_MISSES, replace=False))
        approach = (55.0, 42.0, 30.0, 20.0, None, 20.0, 32.0, 45.0, 58.0)
        for i in picks:
            task = candidates[i]
            center = task["start_time"] + timedelta(minutes=int(self.rng.integers(8, int(task["actual_time_min"]) - 8)))
            closest = round(float(self.rng.uniform(8, 14)), 1)
            bearing = float(self.rng.uniform(0, 360))
            sx, sy = task["_spot"]
            for k, dist in enumerate(approach):
                d = closest if dist is None else dist
                ts = center + timedelta(minutes=k - 4)
                tracks[NEAR_MISS_WORKER].append((ts, sx + d * math.sin(math.radians(bearing)),
                                                 sy + d * math.cos(math.radians(bearing))))
            direction = relative_direction(bearing)
            self.out["near_misses"].append({
                "timestamp": center, "machine_id": task["machine_id"], "operator_id": task["operator_id"],
                "worker_id": NEAR_MISS_WORKER, "type": "proximity",
                "description": f"Worker {NEAR_MISS_WORKER} entered {direction}-side swing zone at {closest} m",
                "distance_m": closest, "direction": direction, "severity": proximity_severity(closest),
                "_task": task,
            })
            self._label("proximity_near_miss", center,
                        f"{NEAR_MISS_WORKER} repeatedly enters {NEAR_MISS_MACHINE} swing zone ({closest} m)",
                        operator_id=task["operator_id"], machine_id=task["machine_id"],
                        worker_id=NEAR_MISS_WORKER, task=task)

        # Scripted demo approach during T001.
        dx, dy = DEMO_SPOT
        for k, d in enumerate(demo.WORKER_APPROACH_DISTANCES_M):
            ts = self.demo_task["start_time"] + timedelta(minutes=demo.WORKER_APPROACH_START_MINUTE + k)
            b = math.radians(demo.WORKER_APPROACH_BEARING_DEG)
            tracks[NEAR_MISS_WORKER].append((ts, dx + d * math.sin(b), dy + d * math.cos(b)))

        # 10-minute baseline for every worker, keeping clear of their override tracks.
        zone_names = list(ZONES)
        busy: dict[str, list[tuple[datetime, datetime]]] = defaultdict(list)
        for worker_id, points in tracks.items():
            for ts, _, _ in points:
                busy[worker_id].append((ts - timedelta(minutes=10), ts + timedelta(minutes=10)))
        n_points = (HALF_SHIFTS[-1][1] - HALF_SHIFTS[0][0]) // WORKER_GRID_MIN + 1
        rows = []
        for day in range(NUM_DAYS):
            for w in range(NUM_WORKERS):
                worker_id = f"W{w + 1:02d}"
                cx, cy = ZONES[zone_names[w % len(zone_names)]]
                angles = float(self.rng.uniform(0, 2 * math.pi)) + np.cumsum(self.rng.normal(0, 0.2, n_points))
                radii = np.clip(float(self.rng.uniform(90, 150)) + np.cumsum(self.rng.normal(0, 6, n_points)), 80, 160)
                for k in range(n_points):
                    ts = _day_start(day) + timedelta(minutes=HALF_SHIFTS[0][0] + k * WORKER_GRID_MIN)
                    if any(a <= ts <= b for a, b in busy.get(worker_id, ())):
                        continue
                    lat, lon = to_latlon(cx + radii[k] * math.sin(angles[k]), cy + radii[k] * math.cos(angles[k]))
                    rows.append({"timestamp": ts, "worker_id": worker_id, "lat": lat, "lon": lon})
        for worker_id, points in tracks.items():
            for ts, east, north in points:
                lat, lon = to_latlon(east, north)
                rows.append({"timestamp": ts, "worker_id": worker_id, "lat": lat, "lon": lon})
        rows.sort(key=lambda r: (r["timestamp"], r["worker_id"]))
        self.out["worker_positions"] = rows

    def gen_incidents(self) -> None:
        def snapshot(task: dict, before: datetime) -> list[dict]:
            rows = [r for r in self.telemetry_by_task[id(task)] if r["timestamp"] <= before][-3:]
            return [{k: (v.isoformat() if isinstance(v, datetime) else v)
                     for k, v in r.items() if k != "_task"} | {"task_id": task["task_id"]} for r in rows]

        harsh_rows = [r for r in self.out["telemetry"]
                      if r["harsh_events"] >= 2 and r["_task"]["status"] == "completed"]
        picks = sorted(int(i) for i in self.rng.choice(len(harsh_rows), min(NUM_HARSH_INCIDENTS, len(harsh_rows)), replace=False))
        incidents = []
        for i in picks:
            r = harsh_rows[i]
            incidents.append({
                "timestamp": r["timestamp"], "machine_id": r["machine_id"], "operator_id": r["operator_id"],
                "_task": r["_task"], "type": "harsh_event", "severity": "warning",
                "description": f"{r['harsh_events']} harsh events (sudden swing/brake) within one interval",
                "telemetry_snapshot": snapshot(r["_task"], r["timestamp"]), "source": "synthetic",
            })
        for nm in self.out["near_misses"][:3]:
            incidents.append({
                "timestamp": nm["timestamp"], "machine_id": nm["machine_id"], "operator_id": nm["operator_id"],
                "_task": nm["_task"], "type": "near_miss", "severity": "critical",
                "description": f"Operator reported: {nm['description']}",
                "telemetry_snapshot": snapshot(nm["_task"], nm["timestamp"]), "source": "synthetic",
            })
        incidents.sort(key=lambda r: r["timestamp"])
        self.out["incidents"] = incidents

    def gen_training_events(self) -> None:
        metric_names = {"avoidable_idle": "avoidable_idle_min_per_hour", "harsh_events": "harsh_events_per_hour"}

        def rate(op_id: str, trigger: str, days: range) -> float | None:
            engine = sum(self.op_day_stats[(op_id, d)]["engine_min"] for d in days)
            key = "avoidable_idle_min" if trigger == "avoidable_idle" else "harsh"
            value = sum(self.op_day_stats[(op_id, d)][key] for d in days)
            return round(value / (engine / 60), 3) if engine else None

        for op_id, day, trigger, clip_id, completed in TRAINING_PLAN:
            before = rate(op_id, trigger, range(max(0, day - TRAINING_WINDOW_DAYS), day))
            after = rate(op_id, trigger, range(day, min(DEMO_DAY_INDEX, day + TRAINING_WINDOW_DAYS))) if completed else None
            self.out["training_events"].append({
                "operator_id": op_id, "trigger": trigger, "clip_id": clip_id,
                "timestamp": _day_start(day) + timedelta(hours=6, minutes=30), "completed": completed,
                "metric_name": metric_names[trigger], "before_metric": before, "after_metric": after,
            })

    # ------------------------------------------------------------------ finalize
    def finalize(self) -> dict[str, list[dict]]:
        for table in ("telemetry", "near_misses", "incidents", "ground_truth_labels"):
            for row in self.out[table]:
                task = row.pop("_task", None)
                row["task_id"] = task["task_id"] if task else None
        for task in self.out["tasks"]:
            task.pop("_spot", None)
        self.out["tasks"].sort(key=lambda t: (t["start_time"], t["machine_id"]))
        self.out["telemetry"].sort(key=lambda r: (r["timestamp"], r["machine_id"]))
        self.out["ground_truth_labels"].sort(key=lambda r: (r["timestamp"], r["problem"]))
        return dict(self.out)


def generate_dataset(seed: int = SEED) -> dict[str, list[dict]]:
    g = _Generator(seed)
    g.gen_operators()
    g.gen_machines()
    g.gen_weather()
    g.gen_history_and_schedule()
    g.gen_demo_telemetry()
    g.assign_task_ids()
    g.gen_near_misses_and_workers()
    g.gen_incidents()
    g.gen_training_events()
    return g.finalize()


if __name__ == "__main__":
    data = generate_dataset()
    for table, rows in data.items():
        print(f"{table:22s} {len(rows):>7d}")
