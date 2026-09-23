"""Operator insights and the unified ML input payload."""

from datetime import datetime

from pydantic import BaseModel, Field

from app.schemas.core import MachineOut, OperatorOut, TaskOut, TelemetryOut, WeatherOut
from app.schemas.events import TrainingEventOut


class OperatorMetrics(BaseModel):
    tasks_completed: int
    operating_hours: float
    avg_actual_vs_estimate: float | None
    avg_eta_error_min: float | None
    fuel_per_cycle_l: float | None
    fuel_vs_fleet_ratio: float | None  # 1.0 = fleet average on the same machines
    avoidable_idle_min_per_hour: float | None
    legitimate_idle_min_per_hour: float | None  # truck waits - not the operator's fault
    harsh_events_per_hour: float | None
    seatbelt_violations: int
    unbelted_idle_samples: int
    afternoon_pace_ratio: float | None  # cycle time after 15:00 / before 12:00, machine-normalised


class FleetMetrics(BaseModel):
    """Fleet medians of the same metrics."""

    tasks_completed: float | None
    operating_hours: float | None
    avg_actual_vs_estimate: float | None
    avg_eta_error_min: float | None
    fuel_per_cycle_l: float | None
    fuel_vs_fleet_ratio: float | None
    avoidable_idle_min_per_hour: float | None
    legitimate_idle_min_per_hour: float | None
    harsh_events_per_hour: float | None
    seatbelt_violations: float | None
    unbelted_idle_samples: float | None
    afternoon_pace_ratio: float | None


class HourPace(BaseModel):
    hour: int
    avg_cycle_time_s: float
    pace_index: float  # cycle time / machine's fleet average; >1 = slower
    samples: int


class MachineUsage(BaseModel):
    machine_id: str
    tasks: int
    fuel_per_cycle_l: float | None
    fleet_fuel_per_cycle_l: float | None


class SafetySummary(BaseModel):
    alerts: dict[str, int]  # seatbelt | unattended_machine | avoidable_idle -> count
    near_misses: int
    incidents: int


class Habit(BaseModel):
    habit_type: str  # seatbelt | avoidable_idle | harsh_events | afternoon_slowdown | fuel_inefficiency
    count: int | None
    severity: str
    explanation: str
    metric_name: str
    metric: float | None
    fleet_metric: float | None


class InsightsOut(BaseModel):
    operator: OperatorOut
    history_until: datetime  # metrics use data strictly before this (start of today)
    summary: OperatorMetrics
    fleet: FleetMetrics
    pace_by_hour: list[HourPace]
    machines: list[MachineUsage]
    safety: SafetySummary
    habits: list[Habit]
    training: list[TrainingEventOut]


class HistoryTask(TaskOut):
    avg_cycle_time_s: float | None
    fuel_used_l: float | None
    load_cycles: int | None
    avoidable_idle_min: float | None
    truck_wait_idle_min: float | None
    harsh_events: int | None
    seatbelt_alerts: int | None
    temperature: float | None
    rain_mm: float | None
    wind_speed: float | None


class MLInputOut(BaseModel):
    operator: OperatorOut
    machine: MachineOut
    task: TaskOut
    recentTelemetry: list[TelemetryOut] = Field(..., description="Up to 30 rows at or before asOf, oldest first")
    weather: WeatherOut
    history: list[HistoryTask] = Field(..., description="Operator's completed tasks before today, oldest first")
    asOf: datetime


