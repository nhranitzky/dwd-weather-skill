"""
Shared utilities for DWD weather scripts.

Provides geocoding (city name → lat/lon via Nominatim/OSM) and
thin wrappers around the BrightSky API (https://api.brightsky.dev).
"""

from __future__ import annotations

import hashlib
import json as _json
import sys
import time as _time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from rich.console import Console
from rich.table import Table
from rich import box

BRIGHTSKY_BASE = "https://api.brightsky.dev"
NOMINATIM_BASE = "https://nominatim.openstreetmap.org"
USER_AGENT = "dwd-weather-skill/1.0 (contact: openclaw-project)"

CACHE_DIR = Path.home() / ".cache" / "skills" / "dwd-weather"

console = Console()


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(namespace: str, key: str) -> Path:
    h = hashlib.sha256(key.encode()).hexdigest()[:20]
    return CACHE_DIR / f"{namespace}_{h}.json"


def _cache_get(path: Path) -> Any:
    """Return cached data if still valid, else None."""
    try:
        entry = _json.loads(path.read_text())
        if _time.time() < entry["expires"]:
            return entry["data"]
        path.unlink(missing_ok=True)
    except (OSError, KeyError, _json.JSONDecodeError):
        pass
    return None


def _cache_set(path: Path, data: Any, ttl: int) -> None:
    """Write data to cache; silently ignore write errors."""
    try:
        CACHE_DIR.mkdir(parents=True, exist_ok=True)
        path.write_text(_json.dumps({"expires": _time.time() + ttl, "data": data}))
    except OSError:
        pass




# ---------------------------------------------------------------------------
# Geocoding
# ---------------------------------------------------------------------------

def geocode(location: str) -> tuple[float, float, str]:
    """
    Resolve a city/place name to (lat, lon, display_name).

    Uses OpenStreetMap Nominatim – no API key required.
    Results are cached for 7 days. Raises SystemExit on failure.
    """
    cp = _cache_path("geo", location.lower().strip())
    cached = _cache_get(cp)
    if cached:
        return cached["lat"], cached["lon"], cached["display"]

    try:
        resp = requests.get(
            f"{NOMINATIM_BASE}/search",
            params={"q": location, "format": "json", "limit": 1},
            headers={"User-Agent": USER_AGENT},
            timeout=10,
        )
        resp.raise_for_status()
        try:
            results = resp.json()
        except _json.JSONDecodeError:
            console.print("[bold red]Geocoding error:[/] unexpected response (not JSON)")
            sys.exit(1)
    except requests.RequestException as exc:
        console.print(f"[bold red]Geocoding error:[/] {exc}")
        sys.exit(1)
    if not results:
        console.print(f"[bold red]Location not found:[/] {location!r}")
        sys.exit(1)
    r = results[0]
    lat, lon, display = float(r["lat"]), float(r["lon"]), r["display_name"]
    _cache_set(cp, {"lat": lat, "lon": lon, "display": display}, ttl=7 * 86400)
    return lat, lon, display


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
        try:
            return resp.json()
        except _json.JSONDecodeError:
            if optional:
                return None
            console.print("[bold red]BrightSky API error:[/] unexpected response (not JSON)")
            sys.exit(1)
    except requests.HTTPError as exc:
        if optional:
            return None
        status = exc.response.status_code if exc.response is not None else 0
        if status == 404:
            msg = "No data for this location"
        elif status == 429:
            msg = "Rate limit exceeded – please try again later"
        elif 500 <= status < 600:
            msg = f"Service unavailable (HTTP {status}) – try again later"
        else:
            msg = str(exc)
        console.print(f"[bold red]BrightSky API error:[/] {msg}")
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


def fmt_temp(val: float | None, units: str = "dwd") -> str:
    if val is None:
        return "–"
    suffix = "K" if units == "si" else "°C"
    return f"{val:.1f} {suffix}"


def fmt_wind(speed: float | None, direction: int | None = None, units: str = "dwd") -> str:
    if speed is None:
        return "–"
    suffix = "m/s" if units == "si" else "km/h"
    result = f"{speed:.1f} {suffix}"
    if direction is not None:
        result += f"  {_compass(direction)}"
    return result


def fmt_precip(val: float | None, units: str = "dwd") -> str:
    if val is None:
        return "–"
    suffix = "kg/m²" if units == "si" else "mm"
    return f"{val:.1f} {suffix}"


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

def weather_row(r: dict, units: str = "dwd") -> list[str]:
    """Return a list of formatted cells for one hourly weather record."""
    return [
        fmt_timestamp(r.get("timestamp")),
        weather_icon(r),
        fmt_temp(r.get("temperature"), units),
        fmt_precip(r.get("precipitation"), units),
        fmt_wind(r.get("wind_speed"), r.get("wind_direction"), units),
        fmt_humidity(r.get("relative_humidity")),
        fmt_pressure(r.get("pressure_msl")),
        fmt_visibility(r.get("visibility")),
        fmt_sunshine(r.get("sunshine")),
    ]


def print_hourly_table(records: list[dict], title: str, footer: str, units: str) -> None:
    """Print a standard hourly weather table with a footer line."""
    table = make_weather_table(title)
    for r in records:
        table.add_row(*weather_row(r, units))
    console.print()
    console.print(table)
    console.print(f"[dim]  {footer}[/]")
    console.print()


def print_daily_table(
    records: list[dict],
    title: str,
    footer: str,
    units: str,
    *,
    show_icon: bool = False,
    show_avg_temp: bool = False,
    show_humidity: bool = False,
) -> None:
    """Print an aggregated daily weather table with configurable columns."""
    temp_unit = "K" if units == "si" else "°C"
    table = Table(title=title, box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Date", no_wrap=True)
    if show_icon:
        table.add_column("", no_wrap=True)
    table.add_column(f"Min {temp_unit}", justify="right")
    table.add_column(f"Max {temp_unit}", justify="right")
    if show_avg_temp:
        table.add_column(f"Avg {temp_unit}", justify="right")
    table.add_column("Precip", justify="right")
    table.add_column("Avg Wind", justify="right")
    if show_humidity:
        table.add_column("Avg RH", justify="right")
    table.add_column("Sunshine", justify="right")

    for day in aggregate_daily(records):
        row: list[str] = [day["date"]]
        if show_icon:
            row.append(day["icon"])
        row.append(f"{day['temp_min']:.1f}" if day["temp_min"] is not None else "–")
        row.append(f"{day['temp_max']:.1f}" if day["temp_max"] is not None else "–")
        if show_avg_temp:
            row.append(f"{day['temp_avg']:.1f}" if day["temp_avg"] is not None else "–")
        row.append(fmt_precip(day["precip_total"], units))
        row.append(fmt_wind(day["wind_avg"], units=units))
        if show_humidity:
            row.append(f"{day['humidity_avg']:.0f} %" if day["humidity_avg"] is not None else "–")
        row.append(f"{day['sunshine_total']:.0f} min" if day["sunshine_total"] is not None else "–")
        table.add_row(*row)

    console.print()
    console.print(table)
    console.print(f"[dim]  {footer}[/]")
    console.print()


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
