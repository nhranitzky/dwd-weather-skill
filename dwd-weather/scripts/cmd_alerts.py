"""
dwd alerts – Show active DWD weather warnings for a location.

Uses BrightSky /alerts endpoint which proxies DWD CAP alerts.
Alerts are issued by the DWD for Germany only.
"""

from __future__ import annotations

import click
from rich.panel import Panel
from rich.text import Text

from scripts.utils import (
    console,
    geocode,
    brightsky_get,
    fmt_timestamp,
)

SEVERITY_COLORS = {
    "minor": "yellow",
    "moderate": "dark_orange",
    "severe": "red",
    "extreme": "bold red",
}

SEVERITY_ICONS = {
    "minor": "⚠️",
    "moderate": "🟠",
    "severe": "🔴",
    "extreme": "🆘",
}


@click.command()
@click.argument("location", nargs=-1, required=True)
def alerts(location: tuple[str, ...]):
    """Show active DWD weather ALERTS (warnings) for LOCATION.

    Only available for locations within Germany.
    """
    place = " ".join(location)
    lat, lon, display = geocode(place)

    data = brightsky_get("/alerts", {"lat": lat, "lon": lon})
    alert_list = data.get("alerts", [])
    location_info = data.get("location", {})

    console.print()
    municipality = location_info.get("name") or display
    warn_cell = location_info.get("warn_cell_id", "")
    console.print(f"[bold]Weather Alerts[/] – {municipality}"
                  + (f"  [dim](warn cell: {warn_cell})[/]" if warn_cell else ""))
    if not warn_cell:
        console.print("[dim]  ℹ  DWD alerts are only available for locations within Germany.[/]")
    console.print()

    if not alert_list:
        console.print("[bold green]✅  No active weather warnings.[/]")
        console.print()
        return

    for a in alert_list:
        severity = (a.get("severity") or "minor").lower()
        color = SEVERITY_COLORS.get(severity, "yellow")
        icon = SEVERITY_ICONS.get(severity, "⚠️")
        event = a.get("event") or "Weather alert"
        headline = a.get("headline") or event
        description = a.get("description") or ""
        instruction = a.get("instruction") or ""
        onset = fmt_timestamp(a.get("onset"))
        expires = fmt_timestamp(a.get("expires"))

        body = Text()
        body.append(f"{description}\n", style="white")
        if instruction:
            body.append(f"\n📋 {instruction}\n", style="italic dim")
        body.append(f"\n🕐 From: {onset}  →  Until: {expires}", style="dim")

        console.print(Panel(
            body,
            title=f"{icon} [{color}]{headline.upper()}[/]",
            border_style=color,
            expand=False,
        ))
        console.print()
