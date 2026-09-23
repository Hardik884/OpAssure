"""Telemetry replay: PostgreSQL -> live store -> rules -> WebSocket events (handover §10).

Replays the stored telemetry of the demo task (T001: OP1001 on EXC001) in timestamp
order, one row every REPLAY_INTERVAL_SECONDS. For each row, in this order:

    telemetry_update         always
    safety_alert             when a rule (seatbelt / unattended_machine / avoidable_idle) becomes active
    proximity_alert          when the nearest worker's proximity level changes (safe/warning/critical)
    eta_update               when the ETA range or its reason changes meaningfully
    habit_detected           first live occurrence of a behaviour the operator already has as a habit
    training_recommendation  right after habit_detected

Nothing is random: the rows, worker positions and history come from the seeded DB.
Events fire on state *changes*, so a worker standing in the swing zone produces one
critical proximity_alert, not one per tick.
"""

import asyncio
import logging
from collections.abc import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_replay_interval_seconds
from app.db.session import get_session_factory
from app.models import Operator, Task, Telemetry
from app.services import task_service
from app.services.eta_service import MIN_WORKING_SAMPLES, estimate_eta, plan_eta
from app.services.insights_service import operator_habits
from app.services.safety_service import evaluate_proximity
from app.services.safety_state_service import nearest_worker
from app.services.telemetry_service import LiveTelemetryStore, live_store, telemetry_to_dict
from app.services.training_service import CATALOG, recommendations
from app.services.weather_service import WeatherService, weather_service
from app.websocket import events

logger = logging.getLogger("opassure.replay")

DEMO_OPERATOR_ID, DEMO_MACHINE_ID, DEMO_TASK_ID = "OP1001", "EXC001", "T001"
ETA_CHANGE_MIN = 2  # re-send eta_update when min or max moves by this much
RECENT_CYCLE_ROWS = 3

# Live safety alert type -> habit_type it can confirm (insights_service.detect_habits).
ALERT_TO_HABIT = {"seatbelt": "seatbelt", "avoidable_idle": "avoidable_idle"}


class ReplayProcessor:
    """Per-row logic for one replay run. Synchronous and deterministic; holds the run's state."""

    def __init__(self, task: dict, habits: list[dict], recommendations_: list[dict],
                 store: LiveTelemetryStore = live_store, weather: WeatherService = weather_service):
        self.task = task
        self.habits = {h["habit_type"]: h for h in habits}
        self.recommendations = {r["trigger"]: r for r in recommendations_}
        self.store = store
        self.weather = weather
        self.active_alerts: set[str] = set()
        self.proximity_level = "safe"
        self.last_eta: dict | None = None
        self.cycles_done = 0.0
        self.idle_min = 0.0
        self.working_cycles: list[float] = []
        self.live_counts: dict[str, int] = {}
        self.habits_sent: set[str] = set()

    def initial_events(self) -> list[dict]:
        eta = plan_eta(self.task["estimated_time_min"], self.task["estimated_buckets"])
        self.last_eta = eta | {"reason_code": ("plan",)}
        return [events.eta_update(self.task["task_id"], eta, self.task["start_time"])]

    def process(self, db: Session | None, row: dict) -> list[dict]:
        out = [events.telemetry_update(row)]

        # Safety rules (existing engine, via the live store: also updates latest + Black Box buffer).
        alerts = self.store.ingest(row)
        current = {a.type for a in alerts}
        for alert in alerts:
            if alert.type not in self.active_alerts:
                out.append(events.safety_alert(alert, row))
                self.live_counts[alert.type] = self.live_counts.get(alert.type, 0) + 1
        newly_active = current - self.active_alerts
        self.active_alerts = current

        # Proximity from the stored worker positions at this timestamp.
        if db is not None:
            try:
                out.extend(self._proximity(db, row))
            except Exception:  # noqa: BLE001 - a DB hiccup must not stop the replay
                logger.exception("Proximity check failed at %s", row["timestamp"])

        out.extend(self._eta(db, row))
        out.extend(self._habits(newly_active, row))
        return out

    def _proximity(self, db: Session, row: dict) -> list[dict]:
        worker = nearest_worker(db, row["lat"], row["lon"], row["timestamp"])
        alert = evaluate_proximity(worker["distance_m"], row["machine_moving"], worker["direction"]) if worker else None
        level = alert.severity if alert else "safe"
        if level == self.proximity_level:
            return []
        self.proximity_level = level
        return [events.proximity_alert(row["machine_id"], row["timestamp"], level,
                                       worker["distance_m"] if worker else 0.0,
                                       worker["direction"] if worker else None,
                                       worker["worker_id"] if worker else None,
                                       worker["zone"] if worker else "safe")]

    def _eta(self, db: Session | None, row: dict) -> list[dict]:
        self.cycles_done += row["load_cycles"] or 0
        self.idle_min += row["idling_time_min"] or 0
        if row["machine_moving"] and row["avg_cycle_time_s"]:
            self.working_cycles.append(row["avg_cycle_time_s"])
        baseline = recent = None
        if len(self.working_cycles) >= MIN_WORKING_SAMPLES:
            baseline = sum(self.working_cycles[:MIN_WORKING_SAMPLES]) / MIN_WORKING_SAMPLES
            last = self.working_cycles[-RECENT_CYCLE_ROWS:]
            recent = sum(last) / len(last)
        rain = self.weather.get_weather(db, row["timestamp"])["rain_mm"]
        eta = estimate_eta(
            estimated_time_min=self.task["estimated_time_min"], estimated_buckets=self.task["estimated_buckets"],
            elapsed_min=(row["timestamp"] - self.task["start_time"]).total_seconds() / 60,
            cycles_done=self.cycles_done, recent_cycle_s=recent, baseline_cycle_s=baseline,
            working_samples=len(self.working_cycles), idle_min=self.idle_min, rain_mm=rain,
        )
        code = _reason_code(eta["reason"])
        last = self.last_eta
        if last and code == last["reason_code"] and abs(eta["min"] - last["min"]) < ETA_CHANGE_MIN \
                and abs(eta["max"] - last["max"]) < ETA_CHANGE_MIN:
            return []
        self.last_eta = eta | {"reason_code": code}
        return [events.eta_update(self.task["task_id"], eta, row["timestamp"])]

    def _habits(self, newly_active: set[str], row: dict) -> list[dict]:
        out = []
        for alert_type in sorted(newly_active):
            habit_type = ALERT_TO_HABIT.get(alert_type)
            habit = self.habits.get(habit_type)
            if habit is None or habit_type in self.habits_sent:
                continue
            self.habits_sent.add(habit_type)
            count = (habit["count"] or 0) + self.live_counts.get(alert_type, 1)
            at = row["timestamp"].strftime("%H:%M")
            out.append(events.habit_detected(self.task["operator_id"], {
                "habit_type": habit_type, "count": count,
                "explanation": f"{habit['explanation']} Seen again today at {at}.",
            }, row["timestamp"]))
            rec = self.recommendations.get(habit_type)
            if rec is None:  # e.g. training already completed: fall back to the catalog clip
                clip = CATALOG[habit_type]
                rec = {"clip_id": clip["clip_id"], "title": clip["title"], "reason": habit["explanation"]}
            out.append(events.training_recommendation(self.task["operator_id"], rec, row["timestamp"]))
        return out


def _reason_code(reason: str) -> tuple[str, ...]:
    codes = []
    for key, code in (("slowed", "slowdown"), ("Slower", "slowdown"), ("waiting", "waiting"),
                      ("On pace", "on_pace"), ("Behind", "behind"), ("complete", "complete"), ("Plan", "plan")):
        if key in reason and code not in codes:
            codes.append(code)
    return tuple(codes)


def load_replay(db: Session, task_id: str) -> dict:
    """Everything a run needs, read once: task, its telemetry in order, habits and recommendations."""
    task = db.get(Task, task_id)
    if task is None:
        raise LookupError(f"Task {task_id} not found - run `python -m simulator.seed`")
    rows = [telemetry_to_dict(r) for r in db.scalars(
        select(Telemetry).where(Telemetry.task_id == task_id).order_by(Telemetry.timestamp, Telemetry.id))]
    if not rows:
        raise LookupError(f"Task {task_id} has no telemetry to replay")
    operator = db.get(Operator, task.operator_id)
    before, _ = task_service.day_bounds(task_service.get_today(db))
    _, _, habits = operator_habits(db, operator, before)
    recs = recommendations(db, operator, before)["recommendations"]
    task_dict = {c: getattr(task, c) for c in ("task_id", "operator_id", "machine_id", "start_time",
                                                "estimated_time_min", "estimated_buckets")}
    return {"task": task_dict, "rows": rows, "habits": habits, "recommendations": recs}


class ReplayEngine:
    """Owns the single replay loop. start() while running is a no-op; stop() is immediate."""

    def __init__(self, broadcast: Callable[[dict], Awaitable[None]],
                 session_factory: Callable[[], Session] | None = None,
                 store: LiveTelemetryStore = live_store, weather: WeatherService = weather_service):
        self.broadcast = broadcast
        self.session_factory = session_factory or (lambda: get_session_factory()())
        self.store = store
        self.weather = weather
        self._task: asyncio.Task | None = None
        self._stop = asyncio.Event()
        self._lock = asyncio.Lock()
        self._status = {"state": "idle", "taskId": DEMO_TASK_ID, "operatorId": DEMO_OPERATOR_ID,
                        "machineId": DEMO_MACHINE_ID, "rowsSent": 0, "totalRows": None,
                        "intervalSeconds": get_replay_interval_seconds(), "lastTimestamp": None, "error": None}

    @property
    def running(self) -> bool:
        return self._task is not None and not self._task.done()

    def status(self) -> dict:
        return dict(self._status)

    async def start(self, interval: float | None = None, task_id: str = DEMO_TASK_ID) -> tuple[dict, bool]:
        """(status, started). Never creates a second loop."""
        async with self._lock:
            if self.running:
                return self.status(), False
            self._stop = asyncio.Event()
            self._status.update(state="running", taskId=task_id, rowsSent=0, totalRows=None, lastTimestamp=None,
                                error=None, intervalSeconds=get_replay_interval_seconds() if interval is None else interval)
            self._task = asyncio.create_task(self._run(self._status["intervalSeconds"], task_id), name="replay")
            return self.status(), True

    async def stop(self) -> dict:
        async with self._lock:
            if self.running:
                self._stop.set()
                try:
                    await asyncio.wait_for(asyncio.shield(self._task), timeout=10)
                except asyncio.TimeoutError:
                    self._task.cancel()
            return self.status()

    async def reset(self) -> dict:
        await self.stop()
        self.store.clear_machine(self._status["machineId"])
        self._status.update(state="idle", rowsSent=0, totalRows=None, lastTimestamp=None, error=None)
        await self._safe_broadcast(events.replay_status(**self.status()))
        return self.status()

    async def wait(self) -> None:
        if self._task:
            await asyncio.shield(self._task)

    async def _safe_broadcast(self, message: dict) -> None:
        try:
            await self.broadcast(message)
        except Exception:  # noqa: BLE001 - broadcasting must never kill the loop
            logger.exception("Broadcast failed")

    def _process_row(self, processor: ReplayProcessor, row: dict) -> list[dict]:
        try:
            db = self.session_factory()
        except Exception:  # noqa: BLE001
            logger.exception("No DB session for replay row; proximity/weather skipped")
            return processor.process(None, row)
        try:
            return processor.process(db, row)
        finally:
            db.close()

    def _load(self, task_id: str) -> dict:
        db = self.session_factory()
        try:
            return load_replay(db, task_id)
        finally:
            db.close()

    async def _run(self, interval: float, task_id: str) -> None:
        try:
            data = await asyncio.to_thread(self._load, task_id)
        except Exception as exc:  # noqa: BLE001
            logger.exception("Replay could not load task %s", task_id)
            self._status.update(state="error", error=str(exc) if isinstance(exc, LookupError) else "Database unavailable")
            await self._safe_broadcast(events.replay_status(**self.status()))
            return

        task, rows = data["task"], data["rows"]
        self.store.clear_machine(task["machine_id"])
        self._status.update(operatorId=task["operator_id"], machineId=task["machine_id"], totalRows=len(rows))
        processor = ReplayProcessor(task, data["habits"], data["recommendations"], self.store, self.weather)
        logger.info("Replay started: %s (%d rows, %.2fs interval)", task_id, len(rows), interval)
        await self._safe_broadcast(events.replay_status(**self.status()))
        for message in processor.initial_events():
            await self._safe_broadcast(message)

        try:
            for i, row in enumerate(rows):
                if self._stop.is_set():
                    break
                try:
                    messages = await asyncio.to_thread(self._process_row, processor, row)
                except Exception:  # noqa: BLE001 - skip a bad row, keep replaying
                    logger.exception("Replay row %s failed", row.get("timestamp"))
                    continue
                for message in messages:
                    await self._safe_broadcast(message)
                self._status.update(rowsSent=i + 1, lastTimestamp=row["timestamp"].isoformat())
                if i < len(rows) - 1:
                    try:  # interruptible sleep: stop() takes effect immediately
                        await asyncio.wait_for(self._stop.wait(), timeout=interval)
                    except asyncio.TimeoutError:
                        pass
            self._status["state"] = "stopped" if self._stop.is_set() else "finished"
        except asyncio.CancelledError:
            self._status["state"] = "stopped"
            raise
        finally:
            logger.info("Replay %s after %d rows", self._status["state"], self._status["rowsSent"])
            if self._status["state"] != "running":
                await self._safe_broadcast(events.replay_status(**self.status()))
