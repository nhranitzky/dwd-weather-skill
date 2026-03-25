"""
dwd forecast – Show hourly weather forecast for a location.

Uses BrightSky /weather endpoint with future timestamps (MOSMIX model).
Displays up to N days of hourly data in a rich table.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone

import click

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    aggregate_daily,
    print_hourly_table,
    print_daily_table,
)


@click.command()
@click.argument("location", nargs=-1, required=True)
@click.option("--days", "-d", default=3, show_default=True, type=click.IntRange(1, 10),
              help="Number of days to forecast (1–10).")
@click.option("--daily", is_flag=True, default=False,
              help="Show a condensed daily summary instead of hourly rows.")
@click.option("--tz", default="Europe/Berlin", show_default=True)
@click.option("--units", default="dwd", type=click.Choice(["dwd", "si"]), show_default=True)
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
def forecast(location: tuple[str, ...], days: int, daily: bool, tz: str, units: str, output_json: bool):
    """Show weather FORECAST for LOCATION (up to 10 days, hourly or daily)."""
    place = " ".join(location)
    lat, lon, display = geocode(place)

    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)

    data = brightsky_get("/weather", {
        "lat": lat, "lon": lon,
        "date": now.strftime("%Y-%m-%dT%H:%M"),
        "last_date": end.strftime("%Y-%m-%dT%H:%M"),
        "tz": tz, "units": units,
    })

    records = data.get("weather", [])
    if not records:
        console.print("[yellow]No forecast data available for this location.[/]")
        return

    source = (data.get("sources") or [{}])[0]
    station = source.get("station_name") or "MOSMIX forecast"

    if output_json:
        click.echo(_json.dumps({
            "location": display,
            "source": station,
            "records": aggregate_daily(records) if daily else records,
            "mode": "daily" if daily else "hourly",
        }, indent=2, ensure_ascii=False))
        return

    if daily:
        _print_daily(records, display, station, units)
    else:
        _print_hourly(records, display, station, days, units)


def _print_hourly(records: list[dict], display: str, station: str, days: int, units: str):
    footer = f"Station/model: {station}  |  {len(records)} hourly records for {days} day(s)"
    print_hourly_table(records, f"Hourly Forecast – {display}", footer, units)


def _print_daily(records: list[dict], display: str, station: str, units: str):
    print_daily_table(
        records,
        f"Daily Forecast – {display}",
        f"Source: {station}",
        units,
        show_icon=True,
    )
