"""CLI integration tests via click.testing.CliRunner."""
from __future__ import annotations

import json
from unittest.mock import patch

import pytest
from click.testing import CliRunner

from scripts.main import cli


# ---------------------------------------------------------------------------
# Shared test data
# ---------------------------------------------------------------------------

_GEOCODE = (48.137, 11.575, "München, Bayern, Deutschland")

_CURRENT = {
    "weather": {
        "timestamp": "2024-07-15T12:00:00+02:00",
        "temperature": 22.5, "dew_point": 14.0,
        "relative_humidity": 60, "wind_speed": 15.0,
        "wind_direction": 270, "wind_gust_speed": 25.0,
        "wind_gust_direction": 270, "precipitation_10": 0.0,
        "cloud_cover": 20, "pressure_msl": 1015.0,
        "visibility": 20000, "sunshine_30": 25,
        "icon": "clear-day", "condition": "dry",
    },
    "sources": [{"station_name": "München", "distance": 3000}],
}

_WEATHER = {
    "weather": [{
        "timestamp": "2024-07-15T12:00:00+02:00",
        "temperature": 22.5, "precipitation": 0.0,
        "wind_speed": 15.0, "wind_direction": 270,
        "relative_humidity": 60, "pressure_msl": 1015.0,
        "visibility": 20000, "sunshine": 30,
        "icon": "clear-day", "condition": "dry",
    }],
    "sources": [{"station_name": "München"}],
}

_ALERTS = {
    "alerts": [],
    "location": {"name": "München", "warn_cell_id": "901980"},
}

_SOURCES = {
    "sources": [{
        "station_name": "München/Stadt",
        "dwd_station_id": "3668",
        "observation_type": "current",
        "distance": 3000, "height": 515,
        "first_record": "2010-01-01T00:00:00+00:00",
        "last_record": "2024-07-15T12:00:00+00:00",
    }],
}


@pytest.fixture
def runner():
    return CliRunner()


# ---------------------------------------------------------------------------
# current
# ---------------------------------------------------------------------------

def test_current_json(runner):
    with patch("scripts.cmd_current.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_current.brightsky_get", return_value=_CURRENT):
        result = runner.invoke(cli, ["current", "Munich", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "weather" in data
    assert "source" in data


def test_current_units_si_json(runner):
    with patch("scripts.cmd_current.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_current.brightsky_get", return_value=_CURRENT):
        result = runner.invoke(cli, ["current", "Munich", "--units", "si", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["weather"]["temperature"] == 22.5


# ---------------------------------------------------------------------------
# forecast
# ---------------------------------------------------------------------------

def test_forecast_json_hourly(runner):
    with patch("scripts.cmd_forecast.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_forecast.brightsky_get", return_value=_WEATHER):
        result = runner.invoke(cli, ["forecast", "Munich", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "records" in data
    assert data["mode"] == "hourly"


def test_forecast_json_daily(runner):
    with patch("scripts.cmd_forecast.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_forecast.brightsky_get", return_value=_WEATHER):
        result = runner.invoke(cli, ["forecast", "Munich", "--daily", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["mode"] == "daily"


def test_forecast_days_out_of_range(runner):
    result = runner.invoke(cli, ["forecast", "Munich", "--days", "0"])
    assert result.exit_code != 0

    result = runner.invoke(cli, ["forecast", "Munich", "--days", "11"])
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# history
# ---------------------------------------------------------------------------

def test_history_json(runner):
    with patch("scripts.cmd_history.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_history.brightsky_get", return_value=_WEATHER):
        result = runner.invoke(cli, ["history", "Munich", "--date", "2024-07-15", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "records" in data
    assert "period" in data


def test_history_daily_json(runner):
    with patch("scripts.cmd_history.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_history.brightsky_get", return_value=_WEATHER):
        result = runner.invoke(cli, ["history", "Munich", "--date", "2024-07-15", "--daily", "--json"])
    assert result.exit_code == 0
    assert json.loads(result.output)["mode"] == "daily"


def test_history_invalid_date(runner):
    result = runner.invoke(cli, ["history", "Munich", "--date", "not-a-date"])
    assert result.exit_code != 0


def test_history_end_before_start(runner):
    with patch("scripts.cmd_history.geocode", return_value=_GEOCODE):
        result = runner.invoke(
            cli,
            ["history", "Munich", "--date", "2024-07-15", "--end-date", "2024-07-01"],
        )
    assert result.exit_code != 0


# ---------------------------------------------------------------------------
# alerts
# ---------------------------------------------------------------------------

def test_alerts_json(runner):
    with patch("scripts.cmd_alerts.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_alerts.brightsky_get", return_value=_ALERTS):
        result = runner.invoke(cli, ["alerts", "Munich", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "alerts" in data
    assert isinstance(data["alerts"], list)


# ---------------------------------------------------------------------------
# stations
# ---------------------------------------------------------------------------

def test_stations_json(runner):
    with patch("scripts.cmd_stations.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_stations.brightsky_get", return_value=_SOURCES):
        result = runner.invoke(cli, ["stations", "Munich", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "stations" in data
    assert "radius_km" in data


def test_stations_radius_too_low(runner):
    result = runner.invoke(cli, ["stations", "Munich", "--radius", "0"])
    assert result.exit_code != 0


def test_stations_radius_too_high(runner):
    result = runner.invoke(cli, ["stations", "Munich", "--radius", "1001"])
    assert result.exit_code != 0


def test_stations_radius_boundary_values(runner):
    with patch("scripts.cmd_stations.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_stations.brightsky_get", return_value=_SOURCES):
        assert runner.invoke(cli, ["stations", "Munich", "--radius", "1"]).exit_code == 0
        assert runner.invoke(cli, ["stations", "Munich", "--radius", "1000"]).exit_code == 0


# ---------------------------------------------------------------------------
# summary
# ---------------------------------------------------------------------------

def test_summary_json(runner):
    def _brightsky(path, params, **kwargs):
        if path == "/current_weather":
            return _CURRENT
        if path == "/weather":
            return _WEATHER
        return {"alerts": []}

    with patch("scripts.cmd_summary.geocode", return_value=_GEOCODE), \
         patch("scripts.cmd_summary.brightsky_get", side_effect=_brightsky):
        result = runner.invoke(cli, ["summary", "Munich", "--json"])
    assert result.exit_code == 0
    data = json.loads(result.output)
    assert "location" in data
    assert "current" in data
    assert "forecast" in data
    assert "alerts" in data
