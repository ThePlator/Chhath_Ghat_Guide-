"""Distance and direction maths (LLD §3.9).

Python mirror of the functions in static/meeting_spot.html. The widget does the
real work in the browser; tests/test_geo.py and tests/test_meeting_widget.py
pin both implementations to the same values.
"""

from __future__ import annotations

from math import asin, atan2, cos, degrees, radians, sin, sqrt

R_EARTH_M = 6_371_000

# Clockwise from north, 45° each.
COMPASS_POINTS = {
    "hi": ["उत्तर", "उत्तर-पूर्व", "पूर्व", "दक्षिण-पूर्व", "दक्षिण", "दक्षिण-पश्चिम", "पश्चिम", "उत्तर-पश्चिम"],
    "en": ["N", "NE", "E", "SE", "S", "SW", "W", "NW"],
}


def haversine_m(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    p1, p2 = radians(lat1), radians(lat2)
    dp, dl = radians(lat2 - lat1), radians(lon2 - lon1)
    a = sin(dp / 2) ** 2 + cos(p1) * cos(p2) * sin(dl / 2) ** 2
    return 2 * R_EARTH_M * asin(min(1.0, sqrt(a)))


def bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, degrees clockwise from true north."""
    p1, p2 = radians(lat1), radians(lat2)
    dl = radians(lon2 - lon1)
    x = sin(dl) * cos(p2)
    y = cos(p1) * sin(p2) - sin(p1) * cos(p2) * cos(dl)
    return (degrees(atan2(x, y)) + 360) % 360


def compass_point(deg: float, lang: str = "hi") -> str:
    names = COMPASS_POINTS.get(lang, COMPASS_POINTS["hi"])
    return names[round((deg % 360) / 45) % 8]


def round_distance_m(d: float) -> int:
    """≤100 m to the nearest 5 m, else to the nearest 10 m (GPS is ±5–20 m anyway)."""
    step = 5 if d <= 100 else 10
    return int(round(d / step) * step)
