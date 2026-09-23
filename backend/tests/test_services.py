"""DB-free unit tests: rolling buffer, weather fallback, WebSocket event builders."""

from datetime import datetime

import pytest

from app.services.safety_service import SafetyAlert
from app.services.telemetry_service import LiveTelemetryStore
from app.services.weather_service import WeatherService
from app.websocket import events


def _row(minute: int, moving=True, belt="fastened", idle=0.0, task="T001"):
    return {"timestamp": datetime(2025, 6, 29, 7, minute), "machine_id": "EXC001", "operator_id": "OP1001",
            "task_id": task, "engine_hours": 1.0, "fuel_used_l": 0.3, "load_cycles": 2, "avg_cycle_time_s": 22.0,
            "cycle_time_std": 2.0, "idling_time_min": idle, "idle_reason": None if moving else "truck_wait",
            "seatbelt_status": belt, "machine_moving": moving, "harsh_events": 0, "lat": 40.0, "lon": -89.0,
            "safety_alert": None}


class FakeClock:
    def __init__(self):
        self.now = 0.0

    def __call__(self):
        return self.now


def test_rolling_buffer_keeps_last_60_seconds():
    clock = FakeClock()
    store = LiveTelemetryStore(window_s=60, clock=clock)
    for i in range(10):
        clock.now = i * 10.0  # one row every 10 s
        store.ingest(_row(i))
    clock.now = 95.0
    snap = store.snapshot("EXC001")
    assert [r["timestamp"].minute for r in snap] == [4, 5, 6, 7, 8, 9]  # received at 40..90 s
    assert store.snapshot("OTHER") == []


def test_rolling_buffer_row_cap():
    store = LiveTelemetryStore(window_s=3600, max_rows=3, clock=FakeClock())
    for i in range(5):
        store.ingest(_row(i))
    assert len(store.snapshot("EXC001")) == 3


def test_ingest_tracks_idle_streak_and_returns_alerts():
    store = LiveTelemetryStore(clock=FakeClock())
    assert store.ingest(_row(0)) == []
    for i in range(1, 9):
        alerts = store.ingest(_row(i, moving=False, belt="unfastened", idle=1.0))
    assert store.idle_minutes("EXC001") == 8
    assert [a.type for a in alerts] == ["unattended_machine"]
    alerts = store.ingest(_row(9, moving=True, belt="unfastened"))
    assert [(a.type, a.severity) for a in alerts] == [("seatbelt", "critical")]
    assert store.idle_minutes("EXC001") == 0
    store.ingest(_row(10, moving=False, idle=1.0, task="T002"))  # new task resets the streak
    assert store.idle_minutes("EXC001") == 1


OPEN_METEO = {"hourly": {"time": ["2025-06-29T08:00", "2025-06-29T09:00"], "temperature_2m": [16.1, 15.4],
                         "rain": [0.0, 5.2], "wind_speed_10m": [12.0, 20.5], "cloud_cover": [80, 100]}}


def test_weather_live_parses_and_caches():
    calls = []
    svc = WeatherService("live", "http://weather.test/v1/forecast",
                         fetch_json=lambda url: calls.append(url) or OPEN_METEO)
    w = svc.get_weather(None, datetime(2025, 6, 29, 9, 40))
    assert (w["condition"], w["rain_mm"], w["temperature"], w["source"]) == ("heavy_rain", 5.2, 15.4, "live")
    assert svc.get_weather(None, datetime(2025, 6, 29, 9, 5))["source"] == "live"
    assert len(calls) == 1  # cached per hour
    assert svc.get_weather(None, datetime(2025, 6, 29, 8, 0))["condition"] == "cloudy"


def test_weather_falls_back_when_live_fails():
    def boom(url):
        raise TimeoutError("no network")

    svc = WeatherService("live", "http://weather.test", fetch_json=boom)
    w = svc.get_weather(None, datetime(2025, 6, 29, 9, 0))
    assert w["source"] == "fallback"
    assert set(w) == {"timestamp", "condition", "temperature", "rain_mm", "wind_speed", "source"}
    assert svc.get_weather(None, datetime(2025, 6, 29, 9, 0)) == w  # deterministic


def test_weather_synthetic_mode_never_calls_network():
    svc = WeatherService("synthetic", "http://weather.test", fetch_json=lambda url: pytest.fail("network used"))
    assert svc.get_weather(None, datetime(2025, 6, 29, 15, 0))["source"] == "synthetic"


def test_event_envelopes_follow_handover_contract():
    row = _row(5)
    e = events.telemetry_update(row)
    assert set(e) == {"event", "version", "data"}
    assert e["event"] == "telemetry_update" and e["version"] == 1
    assert {"timestamp", "cycleTime", "idle", "fuel", "belt", "movement"} <= set(e["data"])
    assert e["data"]["timestamp"] == "2025-06-29T07:05:00"
    s = events.safety_alert(SafetyAlert("seatbelt", "critical", "msg"), row)["data"]
    assert (s["severity"], s["type"], s["message"]) == ("critical", "seatbelt", "msg")
    p = events.proximity_alert("EXC001", row["timestamp"], "critical", 12.04, "right", "W04", "critical")["data"]
    assert (p["severity"], p["distance"], p["direction"], p["zone"]) == ("critical", 12.0, "right", "critical")
    eta = events.eta_update("T001", {"min": 52, "max": 58, "original": 45, "reason": "Rain slowed cycles",
                                     "bucketsRemaining": 40})["data"]
    assert {"min", "max", "original", "reason", "bucketsRemaining"} <= set(eta)
    h = events.habit_detected("OP1001", {"habit_type": "seatbelt", "count": 3, "explanation": "x"})["data"]
    assert (h["habitType"], h["count"], h["explanation"]) == ("seatbelt", 3, "x")
    t = events.training_recommendation("OP1001", {"clip_id": "C", "title": "T", "reason": "R"})["data"]
    assert (t["clipId"], t["title"], t["reason"]) == ("C", "T", "R")
    with pytest.raises(ValueError):
        events.envelope("nope", {})
