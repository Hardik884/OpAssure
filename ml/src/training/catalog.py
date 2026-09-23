"""Internal training clip catalog.

No external video service — the frontend can point these `clip_id`s at
local/placeholder video assets later. `trigger_types` is what
`src.training.recommend` matches against when picking a clip for a detected
behaviour pattern.
"""

TRAINING_CATALOG = [
    {
        "clip_id": "TR_SEATBELT_TRUCKWAIT",
        "title": "Seatbelt During Truck Waits",
        "topic": "seatbelt",
        "duration_seconds": 45,
        "trigger_types": ["seatbelt_habit"],
    },
    {
        "clip_id": "TR_SWING_ZONE",
        "title": "Safe Swing-Zone Awareness",
        "topic": "proximity",
        "duration_seconds": 50,
        "trigger_types": ["proximity_event"],
    },
    {
        "clip_id": "TR_IDLE_EFFICIENCY",
        "title": "Idle / Engine Efficiency",
        "topic": "idle_efficiency",
        "duration_seconds": 40,
        "trigger_types": ["fuel_inefficiency", "avoidable_idle"],
    },
    {
        "clip_id": "TR_WET_TRENCHING",
        "title": "Wet Soil Trenching",
        "topic": "weather_performance",
        "duration_seconds": 60,
        "trigger_types": ["wet_weather_performance"],
    },
    {
        "clip_id": "TR_HEAT_SAFETY",
        "title": "Working in Heat",
        "topic": "heat_performance",
        "duration_seconds": 55,
        "trigger_types": ["heat_performance"],
    },
    {
        "clip_id": "TR_SAFE_SHUTDOWN",
        "title": "Safe Machine Shutdown",
        "topic": "shutdown",
        "duration_seconds": 35,
        "trigger_types": ["unsafe_shutdown"],
    },
]

_BY_TRIGGER = {}
for _clip in TRAINING_CATALOG:
    for _trigger in _clip["trigger_types"]:
        _BY_TRIGGER.setdefault(_trigger, []).append(_clip)


def get_clip_for_trigger(trigger_type: str) -> dict | None:
    """The first catalog clip matching a trigger type, or None if the
    catalog has no clip for it (a legitimate case — not every possible
    trigger has training content yet)."""
    clips = _BY_TRIGGER.get(trigger_type)
    return clips[0] if clips else None
