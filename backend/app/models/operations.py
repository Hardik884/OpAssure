"""Operational data: tasks, telemetry, worker positions."""

from datetime import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, Float, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Task(Base):
    __tablename__ = "tasks"

    task_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    task_type: Mapped[str] = mapped_column(String(32))
    zone: Mapped[str] = mapped_column(String(8))
    volume_m3: Mapped[float] = mapped_column(Float)
    estimated_buckets: Mapped[int] = mapped_column(Integer)
    weather: Mapped[str] = mapped_column(String(16))  # condition at start_time
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"), index=True)
    operator_skill: Mapped[str] = mapped_column(String(16))
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.machine_id"), index=True)
    machine_age: Mapped[int] = mapped_column(Integer)
    estimated_time_min: Mapped[float] = mapped_column(Float)  # naive plan estimate
    actual_time_min: Mapped[float | None] = mapped_column(Float, nullable=True)  # null until done
    start_time: Mapped[datetime] = mapped_column(DateTime, index=True)
    status: Mapped[str] = mapped_column(String(16))  # completed | scheduled


class Telemetry(Base):
    """One row per sample. Interval fields (fuel_used_l, load_cycles, cycle times,
    idling_time_min, harsh_events) cover the period since the previous sample of the
    same task; state fields (seatbelt_status, machine_moving, lat/lon) are at
    `timestamp`; engine_hours is the machine's cumulative meter."""

    __tablename__ = "telemetry"
    __table_args__ = (
        Index("ix_telemetry_machine_ts", "machine_id", "timestamp"),
        Index("ix_telemetry_operator_ts", "operator_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime)
    machine_id: Mapped[str] = mapped_column(ForeignKey("machines.machine_id"))
    operator_id: Mapped[str] = mapped_column(ForeignKey("operators.operator_id"))
    task_id: Mapped[str | None] = mapped_column(
        ForeignKey("tasks.task_id"), nullable=True, index=True
    )
    engine_hours: Mapped[float] = mapped_column(Float)
    fuel_used_l: Mapped[float] = mapped_column(Float)
    load_cycles: Mapped[int] = mapped_column(Integer)
    avg_cycle_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    cycle_time_std: Mapped[float | None] = mapped_column(Float, nullable=True)
    idling_time_min: Mapped[float] = mapped_column(Float)
    idle_reason: Mapped[str | None] = mapped_column(String(16), nullable=True)
    seatbelt_status: Mapped[str] = mapped_column(String(16))  # fastened | unfastened
    machine_moving: Mapped[bool] = mapped_column(Boolean)
    harsh_events: Mapped[int] = mapped_column(Integer)
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    safety_alert: Mapped[str | None] = mapped_column(String(48), nullable=True)


class WorkerPosition(Base):
    __tablename__ = "worker_positions"
    __table_args__ = (Index("ix_worker_positions_worker_ts", "worker_id", "timestamp"),)

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, index=True)
    worker_id: Mapped[str] = mapped_column(String(16))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
