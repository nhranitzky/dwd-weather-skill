"""
dwd stations – List DWD weather stations near a location.

Uses BrightSky /sources endpoint to discover available observation
stations and their data coverage.
"""

from __future__ import annotations

import json as _json

import click
from rich.table import Table
from rich import box

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    fmt_timestamp,
)


@click.command()
@click.argument("location", nargs=-1, required=True)
@click.option("--radius", "-r", default=50, show_default=True, type=click.IntRange(1, 1000),
              help="Search radius in kilometres (1–1000).")
@click.option("--limit", "-n", default=15, show_default=True, type=int,
              help="Maximum number of stations to display.")
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
def stations(location: tuple[str, ...], radius: int, limit: int, output_json: bool):
    """List DWD observation STATIONS near LOCATION.

    Shows station name, observation type, data coverage dates and distance.
    """
    place = " ".join(location)
    lat, lon, display = geocode(place)

    data = brightsky_get("/sources", {
        "lat": lat, "lon": lon,
        "max_dist": radius * 1000,
    })
    sources = data.get("sources", [])

    if not sources:
        console.print(f"[yellow]No DWD stations found within {radius} km of {display}.[/]")
        return

    sources = sorted(sources, key=lambda s: s.get("distance", 0))[:limit]

    if output_json:
        click.echo(_json.dumps({
            "location": display,
            "radius_km": radius,
            "stations": sources,
        }, indent=2, ensure_ascii=False))
        return

    table = Table(
        title=f"DWD Stations near {display}  (radius: {radius} km)",
        box=box.ROUNDED, show_header=True, header_style="bold cyan",
    )
    table.add_column("#", justify="right", style="dim")
    table.add_column("Station", no_wrap=True)
    table.add_column("DWD ID", style="dim")
    table.add_column("Type", no_wrap=True)
    table.add_column("Dist (km)", justify="right")
    table.add_column("Height (m)", justify="right")
    table.add_column("First Record", no_wrap=True)
    table.add_column("Last Record", no_wrap=True)

    for i, s in enumerate(sources, 1):
        dist_km = s.get("distance", 0) / 1000
        obs_type = (s.get("observation_type") or "?").replace("_", " ")
        table.add_row(
            str(i),
            s.get("station_name") or "?",
            s.get("dwd_station_id") or "?",
            obs_type,
            f"{dist_km:.1f}",
            str(s.get("height") or "?"),
            fmt_timestamp(s.get("first_record"), fmt="%Y-%m-%d"),
            fmt_timestamp(s.get("last_record"), fmt="%Y-%m-%d"),
        )

    console.print()
    console.print(table)
    console.print(f"[dim]  {len(sources)} station(s) shown (of up to {limit} within {radius} km)[/]")
    console.print()
