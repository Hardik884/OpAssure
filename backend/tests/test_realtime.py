"""Realtime: replay of T001 over WS /ws against the seeded test DB (see conftest.py)."""

import time
from datetime import datetime

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app.api.demo import replay_engine
from app.db.session import get_db
from app.main import app
from app.services.eta_service import estimate_eta, plan_eta
from app.services.telemetry_service import live_store
from app.websocket.manager import ConnectionManager

REQUIRED = {"telemetry_update", "safety_alert", "proximity_alert", "eta_update", "habit_detected",
            "training_recommendation"}


@pytest.fixture()
def rt(engine):
    factory = sessionmaker(bind=engine, expire_on_commit=False)

    def override():
        session = factory()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = override
    replay_engine.session_factory = factory
    live_store.clear()
    with TestClient(app) as client:  # one event loop for the whole test, so the replay task survives
        yield client
        client.post("/demo/reset")
    app.dependency_overrides.pop(get_db, None)
    live_store.clear()


def _collect(ws, until_state=("finished", "stopped", "error"), limit=500) -> list[dict]:
    messages = []
    for _ in range(limit):
        m = ws.receive_json()
        messages.append(m)
        if m["event"] == "replay_status" and m["data"]["state"] in until_state:
            return messages
    raise AssertionError("replay did not finish")


@pytest.fixture()
def full_run(rt):
    with rt.websocket_connect("/ws") as ws:
        assert ws.receive_json()["data"]["state"] == "idle"
        assert rt.post("/demo/start", params={"interval": 0}).json()["started"] is True
        return _collect(ws)


def _of(messages, event):
    return [m["data"] for m in messages if m["event"] == event]


def test_ws_connects_and_handles_bad_messages(rt):
    with rt.websocket_connect("/ws") as ws:
        hello = ws.receive_json()
        assert hello["event"] == "replay_status" and hello["version"] == 1
        assert (hello["data"]["operatorId"], hello["data"]["machineId"], hello["data"]["taskId"]) == \
            ("OP1001", "EXC001", "T001")
        ws.send_text("{not json")
        assert ws.receive_json()["event"] == "error"
        ws.send_json({"action": "ping"})
        assert ws.receive_json()["event"] == "pong"


def test_replay_emits_every_event_type(full_run):
    assert {m["event"] for m in full_run} >= REQUIRED
    assert full_run[-1]["data"]["state"] == "finished" and full_run[-1]["data"]["rowsSent"] == 53
    assert all(set(m) == {"event", "version", "data"} for m in full_run)


def test_telemetry_update_contract_and_order(full_run):
    rows = _of(full_run, "telemetry_update")
    assert len(rows) == 53
    assert all({"timestamp", "cycleTime", "idle", "fuel", "belt", "movement"} <= set(r) for r in rows)
    assert all((r["operatorId"], r["machineId"], r["taskId"]) == ("OP1001", "EXC001", "T001") for r in rows)
    stamps = [r["timestamp"] for r in rows]
    assert stamps == sorted(stamps) and len(set(stamps)) == 53
    assert stamps[0] == "2025-06-29T07:31:00" and stamps[-1] == "2025-06-29T08:23:00"


def test_safety_alerts_from_planted_seatbelt_scenario(full_run):
    alerts = [(a["timestamp"], a["type"], a["severity"]) for a in _of(full_run, "safety_alert")]
    assert ("2025-06-29T07:56:00", "unattended_machine", "warning") in alerts
    assert ("2025-06-29T07:57:00", "seatbelt", "critical") in alerts
    assert len(alerts) == len(set(alerts))  # each activation once, not every tick


def test_proximity_critical_once_with_distance_and_direction(full_run):
    prox = _of(full_run, "proximity_alert")
    critical = [p for p in prox if p["severity"] == "critical"]
    assert len(critical) == 1
    assert critical[0]["distance"] < 15 and critical[0]["direction"] == "right" and critical[0]["workerId"] == "W04"
    assert critical[0]["zone"] == "critical"
    assert [p["severity"] for p in prox] == ["warning", "critical", "warning", "safe"]


def test_eta_goes_from_plan_to_rain_delay(full_run):
    etas = _of(full_run, "eta_update")
    assert (etas[0]["min"], etas[0]["max"], etas[0]["original"]) == (45, 45, 45)
    assert all({"min", "max", "original", "reason", "bucketsRemaining"} <= set(e) for e in etas)
    rain = [e for e in etas if "Rain" in e["reason"]]
    assert rain and any(52 <= e["min"] and e["max"] <= 58 for e in rain)
    assert etas[-1]["reason"] == "Task complete" and etas[-1]["bucketsRemaining"] == 0
    assert len(etas) < 20  # only on meaningful change


def test_habit_then_training_recommendation(full_run):
    events = [m["event"] for m in full_run]
    habit = _of(full_run, "habit_detected")
    training = _of(full_run, "training_recommendation")
    assert len(habit) == 1 and len(training) == 1
    assert habit[0]["habitType"] == "seatbelt" and habit[0]["count"] > 1 and habit[0]["explanation"]
    assert (training[0]["clipId"], training[0]["title"]) == ("CLIP_SEATBELT_01", "Buckle up before you move")
    i = events.index("habit_detected")
    assert events[i - 1] == "safety_alert" and events[i + 1] == "training_recommendation"


def test_replay_is_deterministic(rt, full_run):
    with rt.websocket_connect("/ws") as ws:
        ws.receive_json()
        rt.post("/demo/start", params={"interval": 0})
        second = _collect(ws)

    def strip(ms):
        return [(m["event"], m["data"]) for m in ms if m["event"] != "replay_status"]

    assert strip(second) == strip(full_run)


def test_multiple_clients_and_one_disconnects(rt):
    with rt.websocket_connect("/ws") as a:
        a.receive_json()
        with rt.websocket_connect("/ws") as b:
            b.receive_json()
            rt.post("/demo/start", params={"interval": 0.02})
            first_b = [b.receive_json() for _ in range(5)]
        # b disconnected; a must still get the whole replay
        received = _collect(a)
    assert any(m["event"] == "telemetry_update" for m in first_b)
    assert len(_of(received, "telemetry_update")) == 53
    assert received[-1]["data"]["state"] == "finished"


def test_no_duplicate_loops_stop_and_restart(rt):
    first = rt.post("/demo/start", params={"interval": 0.2}).json()
    second = rt.post("/demo/start", params={"interval": 0}).json()
    assert first["started"] is True and second["started"] is False
    time.sleep(0.7)
    stopped = rt.post("/demo/stop").json()["status"]
    assert stopped["state"] == "stopped" and 0 < stopped["rowsSent"] < 53
    time.sleep(0.5)
    assert rt.get("/demo/status").json()["status"]["rowsSent"] == stopped["rowsSent"]  # really stopped

    with rt.websocket_connect("/ws") as ws:
        ws.receive_json()
        assert rt.post("/demo/start", params={"interval": 0}).json()["started"] is True
        rerun = _collect(ws)
    assert rerun[-1]["data"]["state"] == "finished" and len(_of(rerun, "telemetry_update")) == 53


def test_latest_telemetry_follows_replay_and_incident_uses_buffer(rt):
    before = rt.get("/telemetry/latest/EXC001").json()
    assert before["source"] == "database"
    rt.post("/demo/start", params={"interval": 0.15})
    time.sleep(0.6)
    a = rt.get("/telemetry/latest/EXC001").json()
    time.sleep(0.6)
    b = rt.get("/telemetry/latest/EXC001").json()
    assert a["source"] == b["source"] == "live"
    assert a["timestamp"] < b["timestamp"] < before["timestamp"]

    r = rt.post("/incidents", json={"operator_id": "OP1001", "machine_id": "EXC001", "description": "Near miss"})
    assert r.status_code == 201
    body = r.json()
    assert body["snapshot_source"] == "live_buffer" and body["task_id"] == "T001" and body["snapshot_size"] >= 2
    assert rt.get("/demo/status").json()["status"]["state"] == "running"  # incident did not stop the replay

    rt.post("/demo/reset")
    assert rt.get("/telemetry/latest/EXC001").json()["source"] == "database"


def test_replay_reports_error_when_database_fails(rt):
    def broken():
        raise RuntimeError("db down")

    replay_engine.session_factory = broken
    with rt.websocket_connect("/ws") as ws:
        ws.receive_json()
        rt.post("/demo/start", params={"interval": 0})
        final = _collect(ws)[-1]["data"]
    assert final["state"] == "error"
    assert rt.get("/health").status_code == 200


# ------------------------------------------------------------------ unit level
def test_eta_service():
    assert plan_eta(45, 107) == {"min": 45, "max": 45, "original": 45, "reason": "Plan estimate",
                                 "bucketsRemaining": 107}
    common = {"estimated_time_min": 45, "estimated_buckets": 107, "working_samples": 10, "idle_min": 0}
    on_pace = estimate_eta(elapsed_min=10, cycles_done=27, recent_cycle_s=22.5, baseline_cycle_s=22.5, **common)
    assert on_pace["reason"] == "On pace" and on_pace["min"] <= 45 <= on_pace["max"] + 1
    rain = estimate_eta(elapsed_min=33, cycles_done=65, recent_cycle_s=28, baseline_cycle_s=22.5, rain_mm=2.8,
                        **common)
    assert rain["reason"].startswith("Rain (2.8 mm/h) slowed cycles") and rain["min"] > 45
    done = estimate_eta(elapsed_min=53, cycles_done=107.5, recent_cycle_s=28, baseline_cycle_s=22.5, **common)
    assert (done["min"], done["max"], done["bucketsRemaining"], done["reason"]) == (53, 53, 0, "Task complete")
    early = estimate_eta(elapsed_min=1, cycles_done=2, recent_cycle_s=None, baseline_cycle_s=None,
                         **(common | {"working_samples": 1}))
    assert (early["min"], early["max"]) == (45, 45)


class _DeadSocket:
    async def send_json(self, message):
        raise RuntimeError("socket closed")


class _GoodSocket:
    def __init__(self):
        self.received = []

    async def send_json(self, message):
        self.received.append(message)


def test_broadcast_survives_dead_client():
    import asyncio

    mgr = ConnectionManager()
    dead, good = _DeadSocket(), _GoodSocket()
    mgr._clients.update({dead, good})
    asyncio.run(mgr.broadcast({"event": "pong", "version": 1, "data": {}}))
    assert good.received and mgr.count == 1
    asyncio.run(ConnectionManager().broadcast({"event": "pong"}))  # no clients: no-op


def test_event_timestamps_are_iso():
    from app.websocket import events

    e = events.habit_detected("OP1001", {"habit_type": "seatbelt", "count": 2, "explanation": "x"},
                              datetime(2025, 6, 29, 7, 57))
    assert e["data"]["timestamp"] == "2025-06-29T07:57:00"
