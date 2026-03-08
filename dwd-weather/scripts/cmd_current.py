"""
dwd current – Show current weather conditions for a location.

Uses BrightSky /current_weather endpoint which compiles the most recent
SYNOP observation into a single consolidated record.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.table import Table
from rich import box

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    weather_icon,
    fmt_temp,
    fmt_wind,
    fmt_precip,
    fmt_humidity,
    fmt_pressure,
    fmt_visibility,
    fmt_sunshine,
    fmt_timestamp,
)


@click.command()
@click.argument("location", nargs=-1, required=True)
@click.option("--tz", default="Europe/Berlin", show_default=True, help="Timezone for timestamps.")
@click.option("--units", default="dwd", type=click.Choice(["dwd", "si"]), show_default=True,
              help="Unit system: 'dwd' = km/h / mm / °C, 'si' = m/s / kg/m² / K.")
def current(location: tuple[str, ...], tz: str, units: str):
    """Show CURRENT weather for LOCATION (city name or address)."""
    place = " ".join(location)
    lat, lon, display = geocode(place)

    data = brightsky_get("/current_weather", {"lat": lat, "lon": lon, "tz": tz, "units": units})
    w = data.get("weather") or data.get("current_weather", {})
    source = (data.get("sources") or [{}])[0]

    icon = weather_icon(w)
    condition = (w.get("condition") or "").replace("_", " ").title()

    # Build a detail table
    table = Table(box=box.MINIMAL_DOUBLE_HEAD, show_header=False, padding=(0, 2))
    table.add_column("Field", style="bold cyan", no_wrap=True)
    table.add_column("Value")

    rows = [
        ("🕐 Observed at",      fmt_timestamp(w.get("timestamp"))),
        ("🌡️  Temperature",      fmt_temp(w.get("temperature"))),
        ("💧 Dew Point",         fmt_temp(w.get("dew_point"))),
        ("💧 Rel. Humidity",     fmt_humidity(w.get("relative_humidity"))),
        ("🌬️  Wind",             fmt_wind(w.get("wind_speed"), w.get("wind_direction"))),
        ("💨 Gusts",             fmt_wind(w.get("wind_gust_speed"), w.get("wind_gust_direction"))),
        ("☔ Precipitation",     fmt_precip(w.get("precipitation_10"))),
        ("☁️  Cloud Cover",      f"{w.get('cloud_cover')} %" if w.get("cloud_cover") is not None else "–"),
        ("🔵 Pressure (MSL)",    fmt_pressure(w.get("pressure_msl"))),
        ("👁️  Visibility",        fmt_visibility(w.get("visibility"))),
        ("☀️  Sunshine (30 min)", fmt_sunshine(w.get("sunshine_30"))),
    ]
    for field, value in rows:
        table.add_row(field, value)

    station = source.get("station_name") or "unknown station"
    dist_km = source.get("distance", 0) / 1000
    header = f"{icon} {condition}  ·  {display}"
    footer = f"Station: {station}  ({dist_km:.1f} km away)"

    console.print()
    console.print(Panel(table, title=f"[bold green]Current Weather[/] – {header}",
                        subtitle=f"[dim]{footer}[/]", expand=False))
    console.print()
