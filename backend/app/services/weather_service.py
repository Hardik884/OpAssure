"""One weather interface with a guaranteed deterministic fallback (handover §14).

    weather_service.get_weather(db, at) -> {timestamp, condition, temperature, rain_mm, wind_speed, source}

Sources, in order:
  1. live       WEATHER_MODE=live and WEATHER_API_URL set: Open-Meteo-style hourly API,
                cached per hour. Any failure (network, timeout, bad JSON) falls through.
  2. synthetic  the seeded `weather` table (the deterministic demo weather).
  3. synthetic  a fixed formula when the table has no row or the DB is down.
When a live lookup failed, the result's source is "fallback". Never raises.
"""

import json
import logging
import math
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import get_weather_api_url, get_weather_mode
from app.models import Weather
from simulator.generate_data import SITE_LAT, SITE_LON

logger = logging.getLogger("opassure.weather")

LIVE_TIMEOUT_S = 3.0


def condition_from(rain_mm: float, cloudy: bool = False) -> str:
    if rain_mm >= 4:
        return "heavy_rain"
    if rain_mm > 0:
        return "rain"
    return "cloudy" if cloudy else "clear"


def formula_weather(hour: datetime) -> dict:
    """Deterministic last-resort weather: mild day with a diurnal temperature curve, no rain."""
    temp = 20 + 6 * math.sin(2 * math.pi * (hour.hour - 9) / 24)
    return {"timestamp": hour, "condition": "clear", "temperature": round(temp, 1), "rain_mm": 0.0,
            "wind_speed": 10.0, "source": "synthetic"}


def _http_get_json(url: str) -> dict:
    with urllib.request.urlopen(url, timeout=LIVE_TIMEOUT_S) as resp:  # noqa: S310 - URL comes from config
        return json.load(resp)


class WeatherService:
    def __init__(self, mode: str = "synthetic", api_url: str | None = None,
                 fetch_json: Callable[[str], dict] = _http_get_json):
        self.mode = mode
        self.api_url = api_url
        self._fetch_json = fetch_json
        self._cache: dict[datetime, dict] = {}

    @classmethod
    def from_env(cls) -> "WeatherService":
        return cls(mode=get_weather_mode(), api_url=get_weather_api_url())

    def get_weather(self, db: Session | None, at: datetime) -> dict:
        hour = at.replace(minute=0, second=0, microsecond=0)
        live_failed = False
        if self.mode == "live" and self.api_url:
            try:
                return self._live(hour)
            except Exception as exc:  # noqa: BLE001 - any live failure must fall back
                logger.warning("Live weather failed (%s); using synthetic fallback", exc)
                live_failed = True
        result = self._synthetic(db, hour)
        if live_failed:
            result["source"] = "fallback"
        return result

    def _synthetic(self, db: Session | None, hour: datetime) -> dict:
        if db is not None:
            try:
                row = db.get(Weather, hour)
                if row is not None:
                    return {"timestamp": row.timestamp, "condition": row.condition, "temperature": row.temperature,
                            "rain_mm": row.rain_mm, "wind_speed": row.wind_speed, "source": "synthetic"}
            except SQLAlchemyError as exc:
                logger.warning("Weather table unavailable (%s); using formula", exc)
                db.rollback()
        return formula_weather(hour)

    def _live(self, hour: datetime) -> dict:
        if hour in self._cache:
            return dict(self._cache[hour])
        day = hour.date().isoformat()
        query = urllib.parse.urlencode({
            "latitude": SITE_LAT, "longitude": SITE_LON, "start_date": day, "end_date": day,
            "hourly": "temperature_2m,rain,wind_speed_10m,cloud_cover", "timezone": "auto",
        })
        data = self._fetch_json(f"{self.api_url}?{query}")
        hourly = data["hourly"]
        idx = hourly["time"].index(hour.strftime("%Y-%m-%dT%H:00"))
        rain = float(hourly["rain"][idx] or 0.0)
        result = {
            "timestamp": hour,
            "condition": condition_from(rain, cloudy=float(hourly["cloud_cover"][idx] or 0) >= 50),
            "temperature": float(hourly["temperature_2m"][idx]),
            "rain_mm": rain,
            "wind_speed": float(hourly["wind_speed_10m"][idx]),
            "source": "live",
        }
        self._cache[hour] = result
        return dict(result)


weather_service = WeatherService.from_env()
