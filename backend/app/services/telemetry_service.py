"""Telemetry access + the live telemetry store (rolling Black Box buffer).

Rows are handled as plain dicts with the `telemetry` column names, whether they
come from PostgreSQL or from a live source (the replay engine / an ingest call).

Live store
----------
`live_store.ingest(row)` is the single entry point for live telemetry. It
  * appends the row to the machine's rolling buffer (rows received in the last
    60 s of wall-clock time, capped at 600 rows) — the Incident Black Box,
  * remembers it as the machine's latest row,
  * tracks how long the machine has been continuously idle,
  * runs the deterministic safety rules and returns the alerts.
Before any live telemetry arrives, "latest" falls back to the database.
"""

import threading
import time
from collections import deque
from collections.abc import Callable
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Telemetry
from app.services.safety_service import SafetyAlert, evaluate_all

TELEMETRY_FIELDS = (
    "id", "timestamp", "machine_id", "operator_id", "task_id", "engine_hours", "fuel_used_l", "load_cycles",
    "avg_cycle_time_s", "cycle_time_std", "idling_time_min", "idle_reason", "seatbelt_status",
    "machine_moving", "harsh_events", "lat", "lon", "safety_alert",
)
BUFFER_WINDOW_S = 60.0
BUFFER_MAX_ROWS = 600
DB_SNAPSHOT_ROWS = 5


def telemetry_to_dict(row: Telemetry | dict) -> dict:
    if isinstance(row, dict):
        return {f: row.get(f) for f in TELEMETRY_FIELDS}
    return {f: getattr(row, f) for f in TELEMETRY_FIELDS}


def to_jsonable(row: dict) -> dict:
    """For JSON columns (incident snapshots): ISO timestamps."""
    return {k: (v.isoformat() if isinstance(v, datetime) else v) for k, v in row.items()}


class LiveTelemetryStore:
    def __init__(self, window_s: float = BUFFER_WINDOW_S, max_rows: int = BUFFER_MAX_ROWS,
                 clock: Callable[[], float] = time.monotonic):
        self.window_s = window_s
        self.max_rows = max_rows
        self._clock = clock
        self._lock = threading.Lock()
        self._buffers: dict[str, deque[tuple[float, dict]]] = {}
        self._latest: dict[str, dict] = {}
        self._idle_min: dict[str, float] = {}

    def ingest(self, row: dict) -> list[SafetyAlert]:
        """Add one telemetry row; return the safety alerts for the machine's new state."""
        row = telemetry_to_dict(row)
        machine_id = row["machine_id"]
        with self._lock:
            prev = self._latest.get(machine_id)
            same_task = prev is not None and prev.get("task_id") == row.get("task_id")
            if row["machine_moving"]:
                idle = 0.0
            else:
                idle = (self._idle_min.get(machine_id, 0.0) if same_task else 0.0) + float(row["idling_time_min"])
            self._idle_min[machine_id] = idle
            self._latest[machine_id] = row
            buf = self._buffers.setdefault(machine_id, deque(maxlen=self.max_rows))
            buf.append((self._clock(), row))
            self._prune(buf)
        return evaluate_all(seatbelt_status=row["seatbelt_status"], machine_moving=row["machine_moving"],
                            idle_minutes=idle, idle_reason=row["idle_reason"])

    def _prune(self, buf: deque) -> None:
        cutoff = self._clock() - self.window_s
        while buf and buf[0][0] < cutoff:
            buf.popleft()

    def snapshot(self, machine_id: str) -> list[dict]:
        """Rows received for this machine in the last `window_s` seconds, oldest first."""
        with self._lock:
            buf = self._buffers.get(machine_id)
            if not buf:
                return []
            self._prune(buf)
            return [row for _, row in buf]

    def latest(self, machine_id: str) -> dict | None:
        return self._latest.get(machine_id)

    def idle_minutes(self, machine_id: str) -> float:
        return self._idle_min.get(machine_id, 0.0)

    def clear(self) -> None:
        with self._lock:
            self._buffers.clear()
            self._latest.clear()
            self._idle_min.clear()


live_store = LiveTelemetryStore()


# ---------------------------------------------------------------- database access
def latest_from_db(db: Session, machine_id: str) -> dict | None:
    row = db.scalars(select(Telemetry).where(Telemetry.machine_id == machine_id)
                     .order_by(Telemetry.timestamp.desc(), Telemetry.id.desc()).limit(1)).first()
    return telemetry_to_dict(row) if row else None


def get_latest(db: Session, machine_id: str, store: LiveTelemetryStore = live_store) -> tuple[dict | None, str]:
    """(row, source) where source is "live" or "database"."""
    live = store.latest(machine_id)
    if live is not None:
        return live, "live"
    return latest_from_db(db, machine_id), "database"


def history(db: Session, machine_id: str, limit: int, task_id: str | None = None) -> list[dict]:
    """The most recent `limit` rows, returned oldest first."""
    q = select(Telemetry).where(Telemetry.machine_id == machine_id)
    if task_id:
        q = q.where(Telemetry.task_id == task_id)
    rows = db.scalars(q.order_by(Telemetry.timestamp.desc(), Telemetry.id.desc()).limit(limit)).all()
    return [telemetry_to_dict(r) for r in reversed(rows)]


def recent_rows(db: Session, machine_id: str, until: datetime, limit: int = DB_SNAPSHOT_ROWS) -> list[dict]:
    rows = db.scalars(select(Telemetry).where(Telemetry.machine_id == machine_id, Telemetry.timestamp <= until)
                      .order_by(Telemetry.timestamp.desc(), Telemetry.id.desc()).limit(limit)).all()
    return [telemetry_to_dict(r) for r in reversed(rows)]


def idle_minutes_from_db(db: Session, latest: dict) -> float:
    """Continuous idle time ending at `latest`: sum idle rows back to the last moving row of the task."""
    if latest["machine_moving"]:
        return 0.0
    rows = recent_rows(db, latest["machine_id"], latest["timestamp"], limit=60)
    total = 0.0
    for row in reversed(rows):
        if row["machine_moving"] or row["task_id"] != latest["task_id"]:
            break
        total += row["idling_time_min"]
    return total
