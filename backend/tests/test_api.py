"""REST contract tests against the seeded test database, incl. the OP1001 / EXC001 / T001 demo path."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.main import app
from app.models import Telemetry
from app.services.telemetry_service import live_store, telemetry_to_dict


def _t001_rows(engine, until: str) -> list[dict]:
    with Session(engine) as s:
        rows = s.scalars(select(Telemetry).where(Telemetry.task_id == "T001",
                                                 Telemetry.timestamp <= datetime.fromisoformat(until))
                         .order_by(Telemetry.timestamp)).all()
        return [telemetry_to_dict(r) for r in rows]


def _replay(engine, until: str) -> None:
    for row in _t001_rows(engine, until):
        live_store.ingest(row)


# ------------------------------------------------------------------ entities
def test_operators(client):
    ops = client.get("/operators").json()
    assert len(ops) == 20 and ops[0]["operator_id"] == "OP1001"
    op = client.get("/operators/OP1001").json()
    assert set(op) == {"operator_id", "name", "skill", "base_speed", "fatigue_start_hour", "heat_sensitivity",
                       "rain_sensitivity", "belt_skip_probability_when_idle"}


def test_not_found_is_clean_json(client):
    r = client.get("/operators/OP9999")
    assert r.status_code == 404
    assert r.json() == {"error": "not_found", "message": "Operator OP9999 not found",
                        "resource": "operator", "id": "OP9999"}
    for path in ("/tasks/T9999", "/telemetry/latest/NOPE", "/telemetry/history/NOPE", "/safety/NOPE",
                 "/incidents/OP9999", "/training/recommendations/OP9999", "/operator/OP9999/insights",
                 "/ml-input/operator/OP9999", "/machines/NOPE"):
        r = client.get(path)
        assert r.status_code == 404, path
        assert r.json()["error"] == "not_found"


def test_tasks_today_returns_t001_for_op1001(client):
    body = client.get("/tasks/today", params={"operator_id": "OP1001"}).json()
    assert body["date"] == "2025-06-29"
    assert body["tasks"][0]["task_id"] == "T001"
    assert all(t["operator_id"] == "OP1001" for t in body["tasks"])
    t001 = client.get("/tasks/T001").json()
    assert (t001["operator_id"], t001["machine_id"], t001["estimated_time_min"]) == ("OP1001", "EXC001", 45.0)
    assert client.get("/tasks/today").status_code == 422  # operator_id required


# ------------------------------------------------------------------ telemetry
def test_telemetry_latest_and_history(client):
    latest = client.get("/telemetry/latest/EXC001").json()
    assert latest["machine_id"] == "EXC001" and latest["source"] == "database"
    hist = client.get("/telemetry/history/EXC001", params={"limit": 50}).json()
    stamps = [r["timestamp"] for r in hist["rows"]]
    assert hist["count"] == 50 and stamps == sorted(stamps)
    assert stamps[-1] == latest["timestamp"]
    t001 = client.get("/telemetry/history/EXC001", params={"task_id": "T001", "limit": 500}).json()
    assert t001["count"] == 53
    assert client.get("/telemetry/history/EXC001", params={"limit": 0}).status_code == 422


def test_latest_prefers_live_rows(client, engine):
    _replay(engine, "2025-06-29T07:40:00")
    latest = client.get("/telemetry/latest/EXC001").json()
    assert latest["source"] == "live" and latest["timestamp"] == "2025-06-29T07:40:00"


# ------------------------------------------------------------------ safety (T001 script)
def test_safety_state_default(client):
    state = client.get("/safety/EXC001").json()
    assert state["status"] in {"safe", "warning", "critical"}
    assert {"alerts", "nearest_worker", "seatbelt_status", "machine_moving", "source"} <= set(state)


def test_safety_unattended_machine_during_truck_wait(client, engine):
    _replay(engine, "2025-06-29T07:56:00")  # 8 min truck wait, unbuckled since 07:51
    state = client.get("/safety/EXC001").json()
    assert state["idle_minutes"] == 8
    assert [(a["type"], a["severity"]) for a in state["alerts"]] == [("unattended_machine", "warning")]


def test_safety_seatbelt_critical_when_moving_unbuckled(client, engine):
    _replay(engine, "2025-06-29T07:57:00")
    state = client.get("/safety/EXC001").json()
    assert state["status"] == "critical"
    assert state["alerts"][0]["type"] == "seatbelt" and state["alerts"][0]["severity"] == "critical"


def test_safety_proximity_critical_when_worker_in_swing_zone(client, engine):
    _replay(engine, "2025-06-29T08:14:00")
    state = client.get("/safety/EXC001").json()
    assert state["nearest_worker"]["worker_id"] == "W04"
    assert state["nearest_worker"]["direction"] == "right"
    assert state["nearest_worker"]["distance_m"] < 15
    assert ("proximity", "critical") in [(a["type"], a["severity"]) for a in state["alerts"]]


# ------------------------------------------------------------------ incidents
def test_create_incident_with_live_snapshot(client, engine):
    _replay(engine, "2025-06-29T08:14:00")
    r = client.post("/incidents", json={"operator_id": "OP1001", "machine_id": "EXC001", "type": "near_miss",
                                        "severity": "critical", "description": "Worker in right swing zone"})
    assert r.status_code == 201
    body = r.json()
    assert body["snapshot_source"] == "live_buffer"
    assert body["snapshot_size"] == len(body["telemetry_snapshot"]) > 0
    assert body["task_id"] == "T001" and body["timestamp"] == "2025-06-29T08:14:00"
    assert body["telemetry_snapshot"][-1]["timestamp"] == "2025-06-29T08:14:00"

    history = client.get("/incidents/OP1001").json()
    saved = next(i for i in history["incidents"] if i["id"] == body["id"])
    assert saved["telemetry_snapshot"] == body["telemetry_snapshot"]


def test_create_incident_falls_back_to_db_snapshot(client):
    r = client.post("/incidents", json={"task_id": "T001", "description": "Manual report"})
    assert r.status_code == 201
    body = r.json()
    assert (body["operator_id"], body["machine_id"], body["type"]) == ("OP1001", "EXC001", "manual_report")
    assert body["snapshot_source"] == "database" and body["snapshot_size"] == 5


def test_create_incident_validation(client):
    cases = [
        ({"operator_id": "OP1001", "machine_id": "EXC001"}, 422),  # description missing
        ({"description": "x"}, 422),  # no operator/machine/task
        ({"operator_id": "OP1001", "machine_id": "EXC001", "description": "x", "severity": "extreme"}, 422),
        ({"operator_id": "OP1001", "machine_id": "EXC001", "description": "x", "unknown": 1}, 422),
        ({"task_id": "T001", "operator_id": "OP1002", "description": "x"}, 422),  # mismatch
        ({"operator_id": "OP1001", "machine_id": "NOPE", "description": "x"}, 404),
        ({"task_id": "T9999", "description": "x"}, 404),
    ]
    for payload, status in cases:
        r = client.post("/incidents", json=payload)
        assert r.status_code == status, payload
        assert "error" in r.json() and "message" in r.json()


# ------------------------------------------------------------------ insights + training
def test_insights_detect_planted_habits(client):
    def habits(op):
        return {h["habit_type"] for h in client.get(f"/operator/{op}/insights").json()["habits"]}

    body = client.get("/operator/OP1001/insights").json()
    assert body["history_until"] == "2025-06-29T00:00:00"
    assert body["summary"]["seatbelt_violations"] > 10
    assert body["pace_by_hour"] and body["machines"] and "alerts" in body["safety"]
    assert {"seatbelt", "afternoon_slowdown"} <= habits("OP1001")
    assert "afternoon_slowdown" in habits("OP1012")
    assert "fuel_inefficiency" in habits("OP1015")
    assert "fuel_inefficiency" not in habits("OP1001")


def test_training_recommend_then_complete(client):
    recs = client.get("/training/recommendations/OP1001").json()
    triggers = [r["trigger"] for r in recs["recommendations"]]
    assert triggers[0] == "seatbelt"  # safety first
    seatbelt = recs["recommendations"][0]
    assert seatbelt["clip_id"] == "CLIP_SEATBELT_01" and seatbelt["status"] == "recommended"

    r = client.post("/training/complete", json={"operator_id": "OP1001", "clip_id": "CLIP_SEATBELT_01"})
    assert r.status_code == 200
    event = r.json()["training_event"]
    assert r.json()["created"] is True
    assert event["completed"] is True and event["before_metric"] == seatbelt["current_metric"]

    after = client.get("/training/recommendations/OP1001").json()
    assert "seatbelt" not in [x["trigger"] for x in after["recommendations"]]
    assert "CLIP_SEATBELT_01" in [c["clip_id"] for c in after["completed"]]


def test_training_complete_existing_assignment(client):
    recs = client.get("/training/recommendations/OP1011").json()["recommendations"]
    assert ("avoidable_idle", "assigned") in [(r["trigger"], r["status"]) for r in recs]
    r = client.post("/training/complete", json={"operator_id": "OP1011", "clip_id": "CLIP_IDLE_01",
                                                "after_metric": 4.0})
    body = r.json()
    assert body["created"] is False
    assert body["training_event"]["before_metric"] is not None and body["training_event"]["after_metric"] == 4.0


def test_training_complete_validation(client):
    assert client.post("/training/complete", json={"operator_id": "OP1001", "clip_id": "NOPE"}).status_code == 422
    assert client.post("/training/complete", json={"operator_id": "OP9999", "clip_id": "CLIP_IDLE_01"}).status_code == 404
    assert client.post("/training/complete", json={"clip_id": "CLIP_IDLE_01"}).status_code == 422


# ------------------------------------------------------------------ ML input
def test_ml_input_unified_payload(client):
    body = client.get("/ml-input/operator/OP1001").json()
    assert set(body) == {"operator", "machine", "task", "recentTelemetry", "weather", "history", "asOf"}
    assert body["task"]["task_id"] == "T001" and body["machine"]["machine_id"] == "EXC001"
    assert body["asOf"] == "2025-06-29T07:30:00"
    assert body["recentTelemetry"] and all(r["timestamp"] <= body["asOf"] for r in body["recentTelemetry"])
    assert body["history"] and all(h["start_time"] < "2025-06-29" for h in body["history"])
    assert body["history"][0]["avg_cycle_time_s"] is not None
    assert set(body["weather"]) == {"timestamp", "condition", "temperature", "rain_mm", "wind_speed", "source"}


def test_ml_input_as_of_during_task(client, engine):
    body = client.get("/ml-input/operator/OP1001", params={"as_of": "2025-06-29T08:05:00"}).json()
    rows = body["recentTelemetry"]
    assert rows[-1]["timestamp"] == "2025-06-29T08:05:00" and rows[-1]["task_id"] == "T001"
    assert body["weather"]["condition"] == "rain"  # scripted rain from 08:00

    _replay(engine, "2025-06-29T07:45:00")  # live replay moves the default asOf
    assert client.get("/ml-input/operator/OP1001").json()["asOf"] == "2025-06-29T07:45:00"
    assert client.get("/ml-input/operator/OP1001", params={"task_id": "T002"}).status_code == 422


# ------------------------------------------------------------------ infrastructure
def test_database_errors_are_clean_503(client):
    def broken_db():
        raise OperationalError("SELECT 1", {}, Exception("connection refused"))
        yield  # pragma: no cover

    app.dependency_overrides[get_db] = broken_db
    r = client.get("/operators")
    assert r.status_code == 503
    assert r.json() == {"error": "database_error", "message": "Database unavailable or query failed"}


def test_weather_endpoint(client):
    body = client.get("/weather", params={"at": "2025-06-29T09:20:00"}).json()
    assert (body["condition"], body["rain_mm"], body["source"]) == ("heavy_rain", 5.6, "synthetic")
