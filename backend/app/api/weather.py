from datetime import datetime

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models import Telemetry
from app.schemas.core import WeatherOut
from app.services.weather_service import weather_service

router = APIRouter(tags=["weather"])


@router.get("/weather", response_model=WeatherOut, summary="Weather at a time (synthetic fallback always works)")
def get_weather(at: datetime | None = Query(None, description="Default: time of the latest telemetry row"),
                db: Session = Depends(get_db)):
    if at is None:
        try:
            at = db.scalar(select(func.max(Telemetry.timestamp))) or datetime.now()
        except SQLAlchemyError:  # weather must survive a DB outage
            db.rollback()
            at = datetime.now()
    return weather_service.get_weather(db, at)
