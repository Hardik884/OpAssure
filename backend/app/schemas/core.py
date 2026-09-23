"""Response schemas for the core entities. Field names = DB column names (CLAUDE.md §10)."""

from datetime import date, datetime

from pydantic import BaseModel, ConfigDict


class _ORM(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class OperatorOut(_ORM):
    operator_id: str
    name: str
    skill: str
    base_speed: float
    fatigue_start_hour: int
    heat_sensitivity: float
    rain_sensitivity: float
    belt_skip_probability_when_idle: float


class MachineOut(_ORM):
    machine_id: str
    type: str
    model: str
    age_years: int
    health_drift: float


class TaskOut(_ORM):
    task_id: str
    task_type: str
    zone: str
    volume_m3: float
    estimated_buckets: int
    weather: str
    operator_id: str
    operator_skill: str
    machine_id: str
    machine_age: int
    estimated_time_min: float
    actual_time_min: float | None
    start_time: datetime
    status: str


class TodayTasksOut(BaseModel):
    date: date
    operator_id: str
    tasks: list[TaskOut]


class TelemetryOut(_ORM):
    id: int | None = None  # null for live rows not yet stored
    timestamp: datetime
    machine_id: str
    operator_id: str
    task_id: str | None
    engine_hours: float
    fuel_used_l: float
    load_cycles: int
    avg_cycle_time_s: float | None
    cycle_time_std: float | None
    idling_time_min: float
    idle_reason: str | None
    seatbelt_status: str
    machine_moving: bool
    harsh_events: int
    lat: float
    lon: float
    safety_alert: str | None


class LatestTelemetryOut(TelemetryOut):
    source: str  # live (replay/ingest) | database


class TelemetryHistoryOut(BaseModel):
    machine_id: str
    count: int
    rows: list[TelemetryOut]


class WeatherOut(BaseModel):
    timestamp: datetime
    condition: str
    temperature: float
    rain_mm: float
    wind_speed: float
    source: str  # synthetic | live | fallback
