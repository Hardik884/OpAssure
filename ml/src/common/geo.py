"""Minimal geo helpers for the synthetic site.

The site is small (a few hundred meters across), so a flat-earth (equirectangular)
approximation is accurate enough — no need for a full haversine implementation.
"""

import math

_METERS_PER_DEGREE_LAT = 111_320.0


def distance_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Approximate distance in meters between two nearby lat/lon points."""
    mean_lat_rad = math.radians((lat1 + lat2) / 2.0)
    meters_per_degree_lon = _METERS_PER_DEGREE_LAT * math.cos(mean_lat_rad)
    dy = (lat2 - lat1) * _METERS_PER_DEGREE_LAT
    dx = (lon2 - lon1) * meters_per_degree_lon
    return math.hypot(dx, dy)
