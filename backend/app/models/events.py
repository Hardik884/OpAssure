"""Safety events, ground truth and training."""

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.machine_id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"), index=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.task_id"), nullable=True)
    type: Mapped[str] = mapped_column(String(32))  # harsh_event | near_miss | manual_report ...
    severity: Mapped[str] = mapped_column(String(16))  # info | warning | critical
    description: Mapped[str] = mapped_column(Text)
    # Black Box: telemetry rows leading up to the incident.
    telemetry_snapshot: Mapped[list[dict[str, Any]] | None] = mapped_column(JSON, nullable=True)
    source: Mapped[str] = mapped_column(String(16))  # synthetic | operator


class NearMiss(Base):
    __tablename__ = "near_misses"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.machine_id"), index=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"))
    worker_id: Mapped[str] = mapped_column(String(16))
    type: Mapped[str] = mapped_column(String(32))  # proximity
    description: Mapped[str] = mapped_column(Text)
    distance_m: Mapped[float] = mapped_column(Float)  # closest approach
    direction: Mapped[str] = mapped_column(String(8))  # front | right | rear | left
    severity: Mapped[str] = mapped_column(String(16))  # safe | caution | critical


class GroundTruthLabel(Base):
    """Who / when / which planted problem. `expected_detection` says whether a
    detector is expected to flag this case (e.g. early, sub-threshold machine
    degradation is labelled but not expected to be caught)."""

    __tablename__ = "ground_truth_labels"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    problem: Mapped[str] = mapped_column(String(32), index=True)
    operator_id: Mapped[str | None] = mapped_column(ForeignKey("operators.operator_id"), nullable=True)
    machine_id: Mapped[str | None] = mapped_column(ForeignKey("machines.machine_id"), nullable=True)
    worker_id: Mapped[str | None] = mapped_column(String(16), nullable=True)
    task_id: Mapped[str | None] = mapped_column(ForeignKey("tasks.task_id"), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    expected_detection: Mapped[bool] = mapped_column(Boolean)
    description: Mapped[str] = mapped_column(Text)


class TrainingEvent(Base):
    __tablename__ = "training_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"), index=True)
    trigger: Mapped[str] = mapped_column(String(32))
    clip_id: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    completed: Mapped[bool] = mapped_column(Boolean)
    metric_name: Mapped[str] = mapped_column(String(48))
    before_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
    after_metric: Mapped[float | None] = mapped_column(Float, nullable=True)
