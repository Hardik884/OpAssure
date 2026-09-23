"""Bridge between the backend's PostgreSQL data and the `ml/` package.

The `ml/` package (see `ml/README.md` and `ml/docs/integration.md`) is a
standalone Python package that works on pandas DataFrames loaded from CSVs
in `data/synthetic/`. The backend's data lives in PostgreSQL instead, with
a schema that is close to but not identical to the ML layer's — a few
category values differ (see the `_map_*` constants below). This module is
the ONLY place that difference is handled: it queries the database, builds
the DataFrames the `ml/` package expects, and calls its real entry points
(`generate_operator_state`, `update_operator_state`). No ML logic is
duplicated here — this is purely a data-shape adapter.

Caching: building the full `tables` dict and training the ETA model are
both too expensive to redo on every HTTP request (a few seconds each — see
`ml/docs/integration.md` §7's measured timings). They're cached at module
level and only rebuilt when `refresh_ml_cache()` is called explicitly
(wired to the demo reset/seed endpoints). The current task's own recent
telemetry is always queried fresh, since that's exactly what changes live
during the replay.
"""

import sys
import threading
from pathlib import Path

import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Machine, NearMiss, Operator, Task, Telemetry, TrainingEvent, Weather

# --- make the `ml/` package importable -------------------------------------
# ml/'s own modules import each other as `from src.xxx import ...`, assuming
# `ml/` itself (not `ml/src/`) is on sys.path — matching how ml/run_*.py
# scripts bootstrap themselves. `backend/` and `ml/` are sibling directories
# under the repo root.
_ML_ROOT = Path(__file__).resolve().parents[3] / "ml"
if str(_ML_ROOT) not in sys.path:
    sys.path.insert(0, str(_ML_ROOT))

from src.eta.model_io import EtaModelBundle  # noqa: E402
from src.eta.train import train_and_select  # noqa: E402
from src.features.build_features import build_task_level_dataset  # noqa: E402
from src.intelligence.operator_state import generate_operator_state as _generate_operator_state  # noqa: E402
from src.intelligence.realtime import update_operator_state as _update_operator_state  # noqa: E402

# --- category-value mapping: backend schema -> ml/ schema ------------------
# The underlying quantities are the same; only the string spellings differ,
# because the two synthetic generators were built independently.
_SKILL_MAP = {"Beginner": "novice", "Intermediate": "intermediate", "Expert": "expert"}
_CONDITION_MAP = {"heavy_rain": "storm"}  # everything else (clear/cloudy/rain) already matches
_IDLE_REASON_MAP = {"truck_wait": "waiting_for_truck", "avoidable": "unnecessary"}
_SEATBELT_MAP = {"fastened": "buckled", "unfastened": "unbuckled"}


def _map_series(s: pd.Series, mapping: dict) -> pd.Series:
    return s.map(lambda v: mapping.get(v, v))


class MLNotReadyError(RuntimeError):
    """Raised when the ML layer can't be used yet (e.g. no completed tasks
    to train an ETA model on). Callers should treat this as "ML
    unavailable right now" and fall back to the deterministic services."""


# --- table builders ----------------------------------------------------------


def _operators_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(Operator)).all()
    df = pd.DataFrame(
        [
            {
                "operator_id": r.operator_id,
                "name": r.name,
                "skill": _SKILL_MAP.get(r.skill, r.skill),
                "base_speed": r.base_speed,
                "fatigue_start_hour": r.fatigue_start_hour,
                "heat_sensitivity": r.heat_sensitivity,
                "rain_sensitivity": r.rain_sensitivity,
                "belt_skip_probability_when_idle": r.belt_skip_probability_when_idle,
            }
            for r in rows
        ]
    )
    return df


def _machines_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(Machine)).all()
    return pd.DataFrame(
        [
            {"machine_id": r.machine_id, "type": r.type, "age_years": r.age_years, "health_drift": r.health_drift}
            for r in rows
        ]
    )


def _weather_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(Weather).order_by(Weather.timestamp)).all()
    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "condition": _CONDITION_MAP.get(r.condition, r.condition),
                "temperature": r.temperature,
                "rain_mm": r.rain_mm,
                "wind_speed": r.wind_speed,
            }
            for r in rows
        ]
    )
    if len(df):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _tasks_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(Task)).all()
    df = pd.DataFrame(
        [
            {
                "task_id": r.task_id,
                "task_type": r.task_type,
                "zone": r.zone,
                "volume_m3": r.volume_m3,
                "estimated_buckets": r.estimated_buckets,
                "weather": _CONDITION_MAP.get(r.weather, r.weather),
                "operator_id": r.operator_id,
                "operator_skill": _SKILL_MAP.get(r.operator_skill, r.operator_skill),
                "machine_id": r.machine_id,
                "machine_age": r.machine_age,
                "estimated_time_min": r.estimated_time_min,
                # Scheduled (not-yet-completed) tasks have no outcome yet.
                # Fall back to the plan estimate as a placeholder — this is
                # NEVER used as a training label (train_and_select() filters
                # to real outcomes only) and never leaks into any other
                # task's historical features (only tasks strictly BEFORE
                # this one in time can ever use it, and a scheduled task is
                # always "today", i.e. last).
                "actual_time_min": r.actual_time_min if r.actual_time_min is not None else r.estimated_time_min,
                "start_time": r.start_time,
                "status": r.status,
            }
            for r in rows
        ]
    )
    if len(df):
        df["start_time"] = pd.to_datetime(df["start_time"])
    return df


def _telemetry_df(db: Session, task_ids: list[str] | None = None) -> pd.DataFrame:
    q = select(Telemetry)
    if task_ids is not None:
        q = q.where(Telemetry.task_id.in_(task_ids))
    rows = db.scalars(q.order_by(Telemetry.timestamp)).all()
    seatbelt = [_SEATBELT_MAP.get(r.seatbelt_status, r.seatbelt_status) for r in rows]
    moving = [bool(r.machine_moving) for r in rows]
    df = pd.DataFrame(
        [
            {
                "timestamp": r.timestamp,
                "machine_id": r.machine_id,
                "operator_id": r.operator_id,
                "task_id": r.task_id,
                "engine_hours": r.engine_hours,
                "fuel_used_l": r.fuel_used_l,
                "load_cycles": r.load_cycles,
                "avg_cycle_time_s": r.avg_cycle_time_s,
                "cycle_time_std": r.cycle_time_std,
                "idling_time_min": r.idling_time_min,
                "idle_reason": _IDLE_REASON_MAP.get(r.idle_reason, r.idle_reason),
                "seatbelt_status": seatbelt[i],
                "machine_moving": moving[i],
                "harsh_events": r.harsh_events,
                "lat": r.lat,
                "lon": r.lon,
                # Derived fresh from the remapped fields to match ml/'s own
                # definition exactly (moving + unbuckled) — backend's
                # `safety_alert` is a broader category field (also covers
                # unattended_machine/avoidable_idle) that ml/ has no concept
                # of, so it isn't reused directly here.
                "safety_alert": bool(seatbelt[i] == "unbuckled" and moving[i]),
            }
            for i, r in enumerate(rows)
        ]
    )
    if len(df):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _near_misses_df(db: Session, tasks_df: pd.DataFrame) -> pd.DataFrame:
    """Backend's `near_misses` table has no `task_id` column (ml/'s does) —
    derive it by matching each near-miss to whichever task was running on
    that machine at that timestamp. Left as None when no task matches;
    every ml/ caller already handles a near-miss with no task_id (it's
    simply not counted toward that specific task)."""
    rows = db.scalars(select(NearMiss).order_by(NearMiss.timestamp)).all()
    records = []
    for r in rows:
        task_id = None
        if len(tasks_df):
            candidates = tasks_df[tasks_df["machine_id"] == r.machine_id]
            for _, t in candidates.iterrows():
                end = t["start_time"] + pd.Timedelta(minutes=float(t["estimated_time_min"] or 0) * 3)
                if t["start_time"] <= r.timestamp <= end:
                    task_id = t["task_id"]
                    break
        records.append(
            {
                "near_miss_id": f"NM{r.id:04d}",
                "timestamp": r.timestamp,
                "worker_id": r.worker_id,
                "machine_id": r.machine_id,
                "task_id": task_id,
                "distance_m": r.distance_m,
            }
        )
    df = pd.DataFrame(records, columns=["near_miss_id", "timestamp", "worker_id", "machine_id", "task_id", "distance_m"])
    if len(df):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def _training_events_df(db: Session) -> pd.DataFrame:
    rows = db.scalars(select(TrainingEvent)).all()
    df = pd.DataFrame(
        [
            {
                "event_id": f"TR{r.id:04d}",
                "operator_id": r.operator_id,
                "timestamp": r.timestamp,
                "module": r.clip_id,
                "trigger": r.trigger,
                "completed": r.completed,
                "score": r.after_metric,
            }
            for r in rows
        ]
    )
    if len(df):
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df


def build_ml_tables(db: Session) -> dict[str, pd.DataFrame]:
    """Build the full `tables` dict `generate_operator_state()` expects,
    from the current database contents."""
    operators_df = _operators_df(db)
    machines_df = _machines_df(db)
    weather_df = _weather_df(db)
    tasks_df = _tasks_df(db)
    telemetry_df = _telemetry_df(db)
    near_misses_df = _near_misses_df(db, tasks_df)
    return {
        "operators": operators_df,
        "machines": machines_df,
        "weather": weather_df,
        "tasks": tasks_df,
        "telemetry": telemetry_df,
        "near_misses": near_misses_df,
    }


# --- process-lifetime cache: tables, feature matrix, trained ETA model -----

_lock = threading.Lock()
_cache: dict = {"tables": None, "features_df": None, "model_bundle": None}


def refresh_ml_cache(db: Session) -> EtaModelBundle:
    """Rebuild tables + feature matrix + retrain the ETA model against the
    CURRENT database contents. Call this once at startup and again after
    `/demo/reset` or `simulator.seed` change the underlying data — NOT on
    every request; see the module docstring."""
    tables = build_ml_tables(db)

    completed = tables["tasks"][tables["tasks"]["status"] == "completed"]
    if len(completed) < 20:
        raise MLNotReadyError(
            f"Only {len(completed)} completed tasks in the database — not enough to train an ETA model. "
            "Run `python -m simulator.seed` first."
        )

    features_df = build_task_level_dataset(
        tables["tasks"], tables["operators"], tables["machines"], tables["weather"], tables["telemetry"]
    )

    train_tables = {**tables, "tasks": completed}
    report = train_and_select(save=False, tables=train_tables)
    model_bundle = EtaModelBundle(
        model=report["_fitted_model"],
        feature_columns=report["feature_columns"],
        model_name=report["selected_model"],
        metrics=report["candidates"][report["selected_model"]],
        residual_quantile_offsets=report["residual_quantiles"]["offsets"],
    )

    with _lock:
        _cache["tables"] = tables
        _cache["features_df"] = features_df
        _cache["model_bundle"] = model_bundle
    return model_bundle


def _cached(db: Session) -> tuple[dict, pd.DataFrame, EtaModelBundle]:
    with _lock:
        ready = _cache["tables"] is not None
    if not ready:
        refresh_ml_cache(db)
    with _lock:
        return _cache["tables"], _cache["features_df"], _cache["model_bundle"]


# --- public entry points (thin wrappers around the real ml/ functions) -----


def get_operator_state(db: Session, operator_id: str, machine_id: str, task_id: str, current_context: dict | None = None) -> dict:
    """Real backend data, in, `ml.src.intelligence.operator_state.generate_operator_state()`
    output, out. Raises the same `ValueError`s that function raises for
    unknown/mismatched IDs, and `MLNotReadyError` if the model hasn't been
    trained yet (not enough completed tasks in the database)."""
    tables, features_df, model_bundle = _cached(db)

    context = dict(current_context or {})

    # IMPORTANT: the demo task's telemetry is fully pre-seeded in Postgres
    # (the whole scripted story, start to finish) — "live" progress during
    # replay is tracked separately in `telemetry_service.live_store`, an
    # in-memory position, NOT by rows appearing in the DB over time. Naively
    # querying "all telemetry rows for this task_id" would always see the
    # task as 100% complete, regardless of where the replay actually is.
    # Mirror the exact `as_of` derivation `ml_input_service.build_ml_input()`
    # uses, so this endpoint agrees with the rest of the API about "now".
    if "as_of" not in context:
        from app.services.telemetry_service import live_store

        live = live_store.latest(machine_id)
        task_row = db.get(Task, task_id)
        if live and live.get("task_id") == task_id:
            context["as_of"] = live["timestamp"]
        elif task_row is not None:
            context["as_of"] = task_row.start_time
        # else: leave "as_of" unset — generate_operator_state() raises its
        # own clear ValueError for the unknown task_id shortly after.

    if "telemetry_so_far" not in context:
        as_of = context.get("as_of")
        fresh = _telemetry_df(db, task_ids=[task_id])
        if as_of is not None and len(fresh):
            fresh = fresh[fresh["timestamp"] <= pd.Timestamp(as_of)]
        context["telemetry_so_far"] = fresh

    with _lock:
        eta_bundle = _cache["model_bundle"] or model_bundle

    return _generate_operator_state(
        operator_id,
        machine_id,
        task_id,
        current_context=context,
        tables=tables,
        features_df=features_df,
    )


def apply_realtime_telemetry(previous_state: dict, new_telemetry_row: dict, weather_row: dict | None = None,
                             task_context: dict | None = None) -> dict:
    """Thin pass-through to `update_operator_state()` — remap the new
    telemetry row's category values the same way `_telemetry_df()` does,
    since this is meant to be called with a raw backend telemetry row."""
    mapped = dict(new_telemetry_row)
    if "seatbelt_status" in mapped:
        mapped["seatbelt_status"] = _SEATBELT_MAP.get(mapped["seatbelt_status"], mapped["seatbelt_status"])
    if "idle_reason" in mapped:
        mapped["idle_reason"] = _IDLE_REASON_MAP.get(mapped["idle_reason"], mapped["idle_reason"])
    if "safety_alert" not in mapped:
        mapped["safety_alert"] = bool(
            mapped.get("seatbelt_status") == "unbuckled" and mapped.get("machine_moving")
        )
    return _update_operator_state(previous_state, mapped, weather_row=weather_row, task_context=task_context)
