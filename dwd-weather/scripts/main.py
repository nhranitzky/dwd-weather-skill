"""
DWD Weather CLI – main entry point.

Usage:
    dwd current   <location>
    dwd forecast  <location> [--days N]
    dwd history   <location> --date YYYY-MM-DD [--end-date YYYY-MM-DD]
    dwd alerts    <location>
    dwd stations  <location> [--radius KM]
    dwd summary   <location> [--days N]
"""

import click
from importlib.metadata import version, PackageNotFoundError

try:
    _version = version("dwd-weather")
except PackageNotFoundError:
    _version = "0.0.0"

from scripts.cmd_current import current
from scripts.cmd_forecast import forecast
from scripts.cmd_history import history
from scripts.cmd_alerts import alerts
from scripts.cmd_stations import stations
from scripts.cmd_summary import summary


@click.group()
@click.version_option(_version, prog_name="weather")
def cli():
    """
    \b
    🌤  DWD Weather – powered by BrightSky (api.brightsky.dev)
    Data from the German Weather Service (Deutscher Wetterdienst).
    """


cli.add_command(current)
cli.add_command(forecast)
cli.add_command(history)
cli.add_command(alerts)
cli.add_command(stations)
cli.add_command(summary)

if __name__ == "__main__":
    cli()
