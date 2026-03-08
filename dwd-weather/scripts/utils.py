"""
Shared utilities for DWD weather scripts.

Provides geocoding (city name → lat/lon via Nominatim/OSM) and
thin wrappers around the BrightSky API (https://api.brightsky.dev).
"""

from __future__ import annotations

import sys
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

import requests
from rich.console import Console
from rich.table import Table
from rich import box

BRIGHTSKY_BASE = "https://api.brightsky.dev"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "dwd-weather-skill/1.0 (contact: openclaw-project)"

console = Console()


# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def geocode(location: str) -> tuple[float, float, str]:
    """
    Resolve a city/place name to (lat, lon, display_name).

    Uses OpenStreetMap Nominatim – no API key required.
    Raises SystemExit on failure.
    """
    try:
        resp = requests.get(
            f"{NOMINATIM_BASE}/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        results = resp.json()
    except requests.RequestException as exc:
        console.print(f"[bold red]Geocoding error:[/] {exc}")
        sys.exit(1)
    if not results:
        console.print(f"[bold red]Location not found:[/] {location!r}")
        sys.exit(1)
    r = results[0]
    return float(r["lat"]), float(r["lon"]), r["display_name"]


# ---------------------------------------------------------------------------
# BrightSky API helpers
# ---------------------------------------------------------------------------

def brightsky_get(path: str, params: dict[str, Any], *, optional: bool = False) -> dict | None:
    """
    Perform a GET request against BrightSky and return parsed JSON.
    If optional=True, returns None on error instead of raising SystemExit.
    """
    url = f"{BRIGHTSKY_BASE}{path}"
    try:
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        return resp.json()
    except requests.HTTPError as exc:
        if optional:
            return None
        console.print(f"[bold red]BrightSky API error:[/] {exc}")
        sys.exit(1)
    except requests.RequestException as exc:
        if optional:
            return None
        console.print(f"[bold red]Network error:[/] {exc}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Formatting helpers
# ---------------------------------------------------------------------------

CONDITION_ICONS = {
    "dry": "☀️",
    "fog": "🌫️",
    "rain": "🌧️",
    "sleet": "🌨️",
    "snow": "❄️",
    "hail": "🌩️",
    "thunderstorm": "⛈️",
    "null": "❓",
}

ICON_MAP = {
    "clear-day": "☀️",
    "clear-night": "🌙",
    "partly-cloudy-day": "⛅",
    "partly-cloudy-night": "🌛",
    "cloudy": "☁️",
    "fog": "🌫️",
    "wind": "🌬️",
    "rain": "🌧️",
    "sleet": "🌨️",
    "snow": "❄️",
    "hail": "🌩️",
    "thunderstorm": "⛈️",
}


def weather_icon(record: dict) -> str:
    icon = record.get("icon") or ""
    condition = record.get("condition") or ""
    return ICON_MAP.get(icon) or CONDITION_ICONS.get(condition, "🌡️")


def fmt_temp(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val:.1f} °C"


def fmt_wind(speed: float | None, direction: int | None = None) -> str:
    if speed is None:
        return "–"
    result = f"{speed:.1f} km/h"
    if direction is not None:
        result += f"  {_compass(direction)}"
    return result


def fmt_precip(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val:.1f} mm"


def fmt_humidity(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val:.0f} %"


def fmt_pressure(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val:.1f} hPa"


def fmt_visibility(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val / 1000:.1f} km" if val >= 1000 else f"{val:.0f} m"


def fmt_sunshine(val: float | None) -> str:
    if val is None:
        return "–"
    return f"{val:.0f} min"


def fmt_timestamp(ts: str | None, fmt: str = "%a %d.%m. %H:%M") -> str:
    if not ts:
        return "–"
    dt = datetime.fromisoformat(ts)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(fmt)


def _compass(degrees: int) -> str:
    dirs = ["N", "NE", "E", "SE", "S", "SW", "W", "NW"]
    idx = round(degrees / 45) % 8
    return dirs[idx]


# ---------------------------------------------------------------------------
# Daily aggregation
# ---------------------------------------------------------------------------

def aggregate_daily(records: list[dict]) -> list[dict]:
    """
    Group hourly weather records by calendar day and compute aggregates.

    Returns a list of dicts (one per day) sorted by date, each containing:
      date, temp_min, temp_max, temp_avg, precip_total, wind_avg,
      humidity_avg, sunshine_total, icon.
    """
    days_map: dict[str, list[dict]] = defaultdict(list)
    for r in records:
        day = (r.get("timestamp") or "")[:10]
        days_map[day].append(r)

    result = []
    for day, hrs in sorted(days_map.items()):
        def col(key: str) -> list:
            return [h[key] for h in hrs if h.get(key) is not None]

        def avg(lst: list) -> float | None:
            return sum(lst) / len(lst) if lst else None

        temps = col("temperature")
        precips = col("precipitation")
        winds = col("wind_speed")
        sunshine = col("sunshine")
        humidity = col("relative_humidity")
        icons = [weather_icon(h) for h in hrs]

        result.append({
            "date": day,
            "temp_min": min(temps) if temps else None,
            "temp_max": max(temps) if temps else None,
            "temp_avg": avg(temps),
            "precip_total": sum(precips) if precips else None,
            "wind_avg": avg(winds),
            "humidity_avg": avg(humidity),
            "sunshine_total": sum(sunshine) if sunshine else None,
            "icon": max(set(icons), key=icons.count) if icons else "🌡️",
        })
    return result


# ---------------------------------------------------------------------------
# Shared table helpers
# ---------------------------------------------------------------------------

def weather_row(r: dict) -> list[str]:
    """Return a list of formatted cells for one hourly weather record."""
    return [
        fmt_timestamp(r.get("timestamp")),
        weather_icon(r),
        fmt_temp(r.get("temperature")),
        fmt_precip(r.get("precipitation")),
        fmt_wind(r.get("wind_speed"), r.get("wind_direction")),
        fmt_humidity(r.get("relative_humidity")),
        fmt_pressure(r.get("pressure_msl")),
        fmt_visibility(r.get("visibility")),
        fmt_sunshine(r.get("sunshine")),
    ]


def make_weather_table(title: str) -> Table:
    """Create a rich Table pre-configured with standard weather columns."""
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Time", style="dim", no_wrap=True)
    table.add_column("", no_wrap=True)       # icon
    table.add_column("Temp", justify="right")
    table.add_column("Precip", justify="right")
    table.add_column("Wind", justify="right")
    table.add_column("RH", justify="right")
    table.add_column("Pressure", justify="right")
    table.add_column("Visibility", justify="right")
    table.add_column("Sunshine", justify="right")
    return table
