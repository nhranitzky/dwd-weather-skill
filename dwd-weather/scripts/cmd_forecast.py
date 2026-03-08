"""
dwd forecast – Show hourly weather forecast for a location.

Uses BrightSky /weather endpoint with future timestamps (MOSMIX model).
Displays up to N days of hourly data in a rich table.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import click
from rich.table import Table
from rich import box

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    make_weather_table,
    weather_row,
    aggregate_daily,
)


@click.command()
@click.argument("location", nargs=-1, required=True)
@click.option("--days", "-d", default=3, show_default=True, type=click.IntRange(1, 10),
              help="Number of days to forecast (1–10).")
@click.option("--daily", is_flag=True, default=False,
              help="Show a condensed daily summary instead of hourly rows.")
@click.option("--tz", default="Europe/Berlin", show_default=True)
@click.option("--units", default="dwd", type=click.Choice(["dwd", "si"]), show_default=True)
def forecast(location: tuple[str, ...], days: int, daily: bool, tz: str, units: str):
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

    if daily:
        _print_daily(records, display, station)
    else:
        _print_hourly(records, display, station, days)


def _print_hourly(records: list[dict], display: str, station: str, days: int):
    table = make_weather_table(f"Hourly Forecast – {display}")
    for r in records:
        table.add_row(*weather_row(r))
    console.print()
    console.print(table)
    console.print(f"[dim]  Station/model: {station}  |  {len(records)} hourly records for {days} day(s)[/]")
    console.print()


def _print_daily(records: list[dict], display: str, station: str):
    """Aggregate hourly records to one row per calendar day."""
    table = Table(
        title=f"Daily Forecast – {display}",
        box=box.ROUNDED, show_header=True, header_style="bold cyan",
    )
    table.add_column("Date", no_wrap=True)
    table.add_column("", no_wrap=True)
    table.add_column("Min °C", justify="right")
    table.add_column("Max °C", justify="right")
    table.add_column("Total Precip", justify="right")
    table.add_column("Avg Wind", justify="right")
    table.add_column("Sunshine", justify="right")

    for day in aggregate_daily(records):
        table.add_row(
            day["date"],
            day["icon"],
            f"{day['temp_min']:.1f}" if day["temp_min"] is not None else "–",
            f"{day['temp_max']:.1f}" if day["temp_max"] is not None else "–",
            f"{day['precip_total']:.1f} mm" if day["precip_total"] is not None else "–",
            f"{day['wind_avg']:.1f} km/h" if day["wind_avg"] is not None else "–",
            f"{day['sunshine_total']:.0f} min" if day["sunshine_total"] is not None else "–",
        )

    console.print()
    console.print(table)
    console.print(f"[dim]  Source: {station}[/]")
    console.print()
