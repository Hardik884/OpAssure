"""Safety, incident and training schemas."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class SafetyAlertOut(BaseModel):
    type: str  # seatbelt | proximity | avoidable_idle | unattended_machine
    severity: str  # warning | critical
    message: str


class NearestWorkerOut(BaseModel):
    worker_id: str
    distance_m: float
    direction: str  # front | right | rear | left
    zone: str  # safe | caution | critical
    timestamp: datetime


class SafetyStateOut(BaseModel):
    machine_id: str
    status: str  # safe | warning | critical
    timestamp: datetime
    operator_id: str
    task_id: str | None
    seatbelt_status: str
    machine_moving: bool
    idle_minutes: float
    idle_reason: str | None
    nearest_worker: NearestWorkerOut | None
    alerts: list[SafetyAlertOut]
    source: str  # live | database


class IncidentCreate(BaseModel):
    """Either task_id, or both operator_id and machine_id, must identify the machine/operator."""

    model_config = ConfigDict(extra="forbid")

    operator_id: str | None = Field(None, max_length=16)
    machine_id: str | None = Field(None, max_length=16)
    task_id: str | None = Field(None, max_length=16)
    type: str = Field("manual_report", min_length=1, max_length=32)
    severity: Literal["info", "warning", "critical"] = "warning"
    description: str = Field(..., min_length=1, max_length=2000)
    timestamp: datetime | None = None  # default: machine's latest telemetry time


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    timestamp: datetime
    machine_id: str
    operator_id: str
    task_id: str | None
    type: str
    severity: str
    description: str
    source: str
    telemetry_snapshot: list[dict[str, Any]] | None


class IncidentCreatedOut(IncidentOut):
    snapshot_source: str  # live_buffer | database | none
    snapshot_size: int


class IncidentListOut(BaseModel):
    operator_id: str
    count: int
    incidents: list[IncidentOut]


class TrainingEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    operator_id: str
    trigger: str
    clip_id: str
    timestamp: datetime
    completed: bool
    metric_name: str
    before_metric: float | None
    after_metric: float | None


class RecommendationOut(BaseModel):
    clip_id: str
    title: str
    trigger: str
    reason: str
    priority: str  # high | medium
    status: str  # recommended | assigned
    metric_name: str
    current_metric: float | None
    fleet_metric: float | None


class RecommendationsOut(BaseModel):
    operator_id: str
    recommendations: list[RecommendationOut]
    completed: list[TrainingEventOut]


class TrainingCompleteIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    operator_id: str = Field(..., min_length=1, max_length=16)
    clip_id: str = Field(..., min_length=1, max_length=32)
    timestamp: datetime | None = None
    before_metric: float | None = None  # default: operator's current metric for this trigger
    after_metric: float | None = None  # usually measured later


class TrainingCompleteOut(BaseModel):
    training_event: TrainingEventOut
    created: bool  # false when an existing assigned training was marked complete
