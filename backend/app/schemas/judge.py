"""Judge Control Panel request bodies (POST /judge/*). See app/api/judge.py."""

from pydantic import BaseModel, ConfigDict, Field


class ProximityInjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    distance_m: float = Field(8.0, gt=0, le=50, description="How close the worker gets, in meters")
    direction: str = Field("right", pattern="^(front|right|rear|left)$")


class RainInjectIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    rain_mm: float = Field(12.0, gt=0, le=50, description="mm/h to report for the current hour")
    cycle_multiplier: float = Field(1.35, gt=1.0, le=3.0, description="Correlated cycle-time hit a rainstorm plausibly causes")


class CycleSpikeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    multiplier: float = Field(1.6, gt=1.0, le=3.0, description="Recent cycle time as a multiple of the task's own baseline")
