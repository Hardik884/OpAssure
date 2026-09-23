"""The shared deterministic demo scenario (handover §22, CLAUDE.md §7).

Operator OP1001 runs task T001 on excavator EXC001 on the last day of the dataset
("demo day"). Unlike the historical data, this task is fully scripted — no random
draws — so every team member replays exactly the same story:

    min  0-17  loading trucks, dry, ~22.5 s cycles (plan ETA = 45 min)
    min 18-25  truck wait (legitimate idle); OP1001 unbuckles at min 20
    min 26-27  resumes digging BEFORE re-buckling -> critical seatbelt alert
    min 30+    rain starts (08:00 weather row) -> cycles slow to ~28 s -> ETA 52-58
    min 40-48  worker W04 walks into the right-side swing zone (closest 12 m)
    ~min 53    task complete

T001 telemetry is stored at 1-minute resolution (the replay script); historical
telemetry is sampled every 5-15 minutes.
"""

from datetime import time

DEMO_OPERATOR_ID = "OP1001"
DEMO_MACHINE_ID = "EXC001"
DEMO_TASK_ID = "T001"
DEMO_WORKER_ID = "W04"

DEMO_TASK_START = time(7, 30)
DEMO_TASK = {
    "task_type": "truck_loading",
    "zone": "A",
    "volume_m3": 160.0,
    "estimated_buckets": 107,
    "estimated_time_min": 45.0,
}

# Demo-day weather overrides: hour -> (condition, temperature C, rain_mm, wind km/h)
DEMO_WEATHER = {
    5: ("cloudy", 15.0, 0.0, 8.0),
    6: ("cloudy", 15.5, 0.0, 9.0),
    7: ("cloudy", 16.5, 0.0, 12.0),
    8: ("rain", 16.0, 2.8, 18.0),
    9: ("heavy_rain", 15.5, 5.6, 24.0),
    10: ("rain", 16.0, 2.2, 19.0),
    11: ("cloudy", 17.5, 0.2, 14.0),
    12: ("cloudy", 18.5, 0.0, 12.0),
}

TRUCK_WAIT_MINUTES = range(18, 26)
UNBUCKLE_MINUTE = 20
MOVE_UNBELTED_MINUTES = range(26, 28)
RAIN_FROM_MINUTE = 30
CYCLE_DRY_S = 22.5
CYCLE_RAIN_S = 28.0
# Deterministic wobble so cycle time is not a flat line in the UI.
CYCLE_WOBBLE_S = (0.0, 0.6, -0.4, 0.9, -0.7, 0.3, -0.2, 0.5)

WORK_FUEL_L_PER_MIN = 17.0 / 60
IDLE_FUEL_L_PER_MIN = 3.0 / 60

# Worker W04 approaches from the machine's right (machine faces north, worker due east).
WORKER_APPROACH_START_MINUTE = 40
WORKER_APPROACH_DISTANCES_M = (48.0, 38.0, 28.0, 19.0, 12.0, 17.0, 29.0, 42.0, 55.0)
WORKER_APPROACH_BEARING_DEG = 90.0
MACHINE_HEADING_DEG = 0.0


def demo_minute_states() -> list[dict]:
    """Minute-by-minute machine/operator state for T001 until all buckets are loaded."""
    states: list[dict] = []
    cycles_done = 0.0
    minute = 0
    belted = True
    while cycles_done < DEMO_TASK["estimated_buckets"]:
        if minute == UNBUCKLE_MINUTE:
            belted = False
        if minute in TRUCK_WAIT_MINUTES:
            states.append(
                {"working": False, "cycle_s": None, "cycles": 0.0, "fuel_l": IDLE_FUEL_L_PER_MIN,
                 "idle_reason": "truck_wait", "belted": belted, "harsh": 0}
            )
        else:
            if minute >= MOVE_UNBELTED_MINUTES.stop:
                belted = True
            base = CYCLE_RAIN_S if minute >= RAIN_FROM_MINUTE else CYCLE_DRY_S
            cycle_s = base + CYCLE_WOBBLE_S[minute % len(CYCLE_WOBBLE_S)]
            cycles = 60.0 / cycle_s
            cycles_done += cycles
            states.append(
                {"working": True, "cycle_s": cycle_s, "cycles": cycles, "fuel_l": WORK_FUEL_L_PER_MIN,
                 "idle_reason": None, "belted": belted, "harsh": 0}
            )
        minute += 1
    return states
