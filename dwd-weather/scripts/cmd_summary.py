"""
dwd summary – A compact weather summary: current conditions + multi-day outlook.

This command combines /current_weather and /weather (forecast) into a single
at-a-glance overview – ideal for a quick terminal weather check.
"""

from __future__ import annotations

import json as _json
from datetime import datetime, timedelta, timezone

import click
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich import box

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    aggregate_daily,
    weather_icon,
    fmt_temp,
    fmt_wind,
    fmt_humidity,
    fmt_pressure,
    fmt_visibility,
    fmt_timestamp,
)


@click.command()
@click.argument("location", nargs=-1, required=True)
@click.option("--days", "-d", default=5, show_default=True, type=click.IntRange(1, 10),
              help="Number of forecast days to include in the outlook.")
@click.option("--tz", default="Europe/Berlin", show_default=True)
@click.option("--units", default="dwd", type=click.Choice(["dwd", "si"]), show_default=True)
@click.option("--json", "output_json", is_flag=True, default=False, help="Output as JSON.")
def summary(location: tuple[str, ...], days: int, tz: str, units: str, output_json: bool):
    """Compact weather SUMMARY: current conditions + multi-day outlook."""
    place = " ".join(location)
    lat, lon, display = geocode(place)

    # Fetch current weather
    cur_data = brightsky_get("/current_weather", {"lat": lat, "lon": lon, "tz": tz, "units": units})
    w = cur_data.get("weather") or cur_data.get("current_weather", {})
    cur_source = (cur_data.get("sources") or [{}])[0]

    # Fetch forecast
    now = datetime.now(timezone.utc)
    end = now + timedelta(days=days)
    fc_data = brightsky_get("/weather", {
        "lat": lat, "lon": lon,
        "date": now.strftime("%Y-%m-%dT%H:%M"),
        "last_date": end.strftime("%Y-%m-%dT%H:%M"),
        "tz": tz, "units": units,
    })
    records = fc_data.get("weather", [])

    # Fetch alerts (best-effort, may 404 outside Germany)
    alert_data = brightsky_get("/alerts", {"lat": lat, "lon": lon}, optional=True)
    alert_list = alert_data.get("alerts", []) if alert_data else []

    if output_json:
        click.echo(_json.dumps({
            "location": display,
            "current": w,
            "current_source": cur_source,
            "forecast": aggregate_daily(records),
            "alerts": alert_list,
        }, indent=2, ensure_ascii=False))
        return

    # ── Current conditions panel ─────────────────────────────────────────────
    icon = weather_icon(w)
    condition = (w.get("condition") or "").replace("_", " ").title()
    temp = fmt_temp(w.get("temperature"))

    cur_text = Text()
    cur_text.append(f"  {icon}  {temp}  {condition}\n\n", style="bold")
    cur_text.append(f"  💨 Wind:     {fmt_wind(w.get('wind_speed'), w.get('wind_direction'))}\n")
    cur_text.append(f"  💧 Humidity: {fmt_humidity(w.get('relative_humidity'))}\n")
    cur_text.append(f"  🔵 Pressure: {fmt_pressure(w.get('pressure_msl'))}\n")
    cur_text.append(f"  👁  Visibility:{fmt_visibility(w.get('visibility'))}\n")
    obs_time = fmt_timestamp(w.get("timestamp"))
    station = cur_source.get("station_name", "?")
    cur_text.append(f"\n  [dim]Observed {obs_time}  ·  {station}[/]")

    cur_panel = Panel(cur_text, title=f"[bold green]Now[/] – {display}", expand=False)

    # ── Alert summary ─────────────────────────────────────────────────────────
    if alert_list:
        worst = max(alert_list, key=lambda a: ["minor","moderate","severe","extreme"].index(
            (a.get("severity") or "minor").lower()
        ))
        alert_text = f"⚠️  [bold red]{worst.get('headline','Alert')}[/]"
        if len(alert_list) > 1:
            alert_text += f"  [dim](+{len(alert_list)-1} more)[/]"
        console.print(Panel(Text.from_markup(alert_text), border_style="red", expand=False))

    console.print(cur_panel)

    # ── Daily outlook table ──────────────────────────────────────────────────
    if not records:
        return

    table = Table(
        title=f"{days}-Day Outlook",
        box=box.SIMPLE_HEAVY, show_header=True, header_style="bold cyan",
    )
    table.add_column("Date", no_wrap=True)
    table.add_column("", no_wrap=True)      # icon
    table.add_column("Low", justify="right")
    table.add_column("High", justify="right")
    table.add_column("Rain", justify="right")
    table.add_column("Wind (avg)", justify="right")
    table.add_column("Sunshine", justify="right")

    for day in aggregate_daily(records):
        table.add_row(
            day["date"],
            day["icon"],
            f"{day['temp_min']:.0f}°" if day["temp_min"] is not None else "–",
            f"{day['temp_max']:.0f}°" if day["temp_max"] is not None else "–",
            f"{day['precip_total']:.1f} mm" if day["precip_total"] is not None else "–",
            f"{day['wind_avg']:.1f} km/h" if day["wind_avg"] is not None else "–",
            f"{day['sunshine_total']:.0f} min" if day["sunshine_total"] is not None else "–",
        )

    console.print(table)
    console.print()
