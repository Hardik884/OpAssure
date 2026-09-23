"""Core entities: operators, machines, weather."""

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base


class Operator(Base):
    __tablename__ = "operators"

    operator_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(100))
    skill: Mapped[str] = mapped_column(String(16))  # Beginner | Intermediate | Expert
    base_speed: Mapped[float] = mapped_column(Float)  # 1.0 = standard pace; higher is faster
    fatigue_start_hour: Mapped[int] = mapped_column(Integer)  # local hour pace starts to drop
    heat_sensitivity: Mapped[float] = mapped_column(Float)  # 0..1
    rain_sensitivity: Mapped[float] = mapped_column(Float)  # 0..1
    belt_skip_probability_when_idle: Mapped[float] = mapped_column(Float)  # 0..1


class Machine(Base):
    __tablename__ = "machines"

    machine_id: Mapped[str] = mapped_column(String(16), primary_key=True)
    type: Mapped[str] = mapped_column(String(16))  # excavator | loader
    model: Mapped[str] = mapped_column(String(32))  # display name, e.g. "CAT 320"
    age_years: Mapped[int] = mapped_column(Integer)
    health_drift: Mapped[float] = mapped_column(Float)  # fractional efficiency loss per day


class Weather(Base):
    __tablename__ = "weather"

    timestamp: Mapped[datetime] = mapped_column(DateTime, primary_key=True)  # hourly
    condition: Mapped[str] = mapped_column(String(16))  # clear | cloudy | rain | heavy_rain
    temperature: Mapped[float] = mapped_column(Float)  # deg C
    rain_mm: Mapped[float] = mapped_column(Float)  # mm in that hour
    wind_speed: Mapped[float] = mapped_column(Float)  # km/h
