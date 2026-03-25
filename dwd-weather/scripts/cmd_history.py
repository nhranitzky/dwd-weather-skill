"""
dwd history – Query historical weather observations for a location.

Uses BrightSky /weather endpoint with past dates. DWD station data goes
back to the early 20th century for some stations.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta

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
@click.option("--date", "-d", required=True, metavar="YYYY-MM-DD",
              help="Start date of the historical period.")
@click.option("--end-date", "-e", default=None, metavar="YYYY-MM-DD",
              help="End date (inclusive). Defaults to --date (single day).")
@click.option("--tz", default="Europe/Berlin", show_default=True)
@click.option("--units", default="dwd", type=click.Choice(["dwd", "si"]), show_default=True)
@click.option("--daily", is_flag=True, default=False,
              help="Show condensed daily summary instead of hourly rows.")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
def history(location: tuple[str, ...], date: str, end_date: str | None,
            tz: str, units: str, daily: bool, output_json: bool):
    """
    Query HISTORICAL weather observations for LOCATION.

    \b
    Examples:
        dwd history Munich --date 2024-07-15
        dwd history Berlin --date 2023-01-01 --end-date 2023-01-31 --daily
    """
    place = " ".join(location)
    lat, lon, display = geocode(place)

    try:
        start_dt = datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        console.print(f"[red]Invalid date format:[/] {date!r}. Use YYYY-MM-DD.")
        raise SystemExit(1)

    if end_date:
        try:
            end_dt = datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            console.print(f"[red]Invalid end-date format:[/] {end_date!r}. Use YYYY-MM-DD.")
            raise SystemExit(1)
        # Include the whole end day
        end_dt = end_dt.replace(hour=23, minute=59)
    else:
        end_dt = start_dt.replace(hour=23, minute=59)

    if end_dt < start_dt:
        console.print("[red]--end-date must be >= --date[/]")
        raise SystemExit(1)

    days = (end_dt - start_dt).days + 1
    if days > 366:
        console.print("[yellow]⚠  Querying more than 1 year – this may take a moment.[/]")

    data = brightsky_get("/weather", {
        "lat": lat, "lon": lon,
        "date": start_dt.strftime("%Y-%m-%d"),
        "last_date": end_dt.strftime("%Y-%m-%dT%H:%M"),
        "tz": tz, "units": units,
    })

    records = data.get("weather", [])
    if not records:
        console.print("[yellow]No historical data found for this location and date range.[/]")
        return

    sources = data.get("sources", [])
    obs_types = list({s.get("observation_type", "?") for s in sources})
    station_names = list({s.get("station_name", "?") for s in sources})
    period = f"{date}" + (f" → {end_date}" if end_date else "")

    if output_json:
        click.echo(_json.dumps({
            "location": display,
            "period": period,
            "stations": station_names,
            "observation_types": obs_types,
            "records": aggregate_daily(records) if daily else records,
            "mode": "daily" if daily else "hourly",
        }, indent=2, ensure_ascii=False))
        return

    if daily:
        _print_daily_summary(records, display, station_names, period, units)
    else:
        _print_hourly(records, display, station_names, period, obs_types, units)


def _print_hourly(records, display, stations, period, obs_types, units):
    footer = (f"Stations: {', '.join(stations)}  |  "
              f"Observation type(s): {', '.join(obs_types)}  |  "
              f"{len(records)} records")
    print_hourly_table(records, f"Historical Weather – {display}  [{period}]", footer, units)


def _print_daily_summary(records, display, stations, period, units):
    print_daily_table(
        records,
        f"Historical Daily Summary – {display}  [{period}]",
        f"Stations: {', '.join(stations)}",
        units,
        show_avg_temp=True,
        show_humidity=True,
    )
