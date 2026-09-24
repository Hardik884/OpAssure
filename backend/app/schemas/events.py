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


class LibraryClipOut(BaseModel):
    """One entry in the full training clip catalog (GET /training/library) —
    the same clip_id/title/metric_name/priority `RecommendationOut` below
    draws from, so a library browse and a live recommendation never disagree
    about what a given clip_id means."""

    clip_id: str
    title: str
    trigger: str  # the habit_type this clip addresses
    metric_name: str
    priority: str  # high | medium


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


class TrainingImpactCaseOut(BaseModel):
    """One measured before/after pair — real numbers from training_events, never modeled."""

    operator_id: str
    operator_name: str
    trigger: str
    clip_title: str
    metric_name: str
    timestamp: datetime
    before_metric: float
    after_metric: float
    pct_change: float | None  # (after - before) / before; negative = improvement for every current metric


class TrainingImpactOut(BaseModel):
    cases: list[TrainingImpactCaseOut]
