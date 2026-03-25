"""Unit tests for scripts/utils.py."""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
import requests

from scripts.utils import (
    aggregate_daily,
    brightsky_get,
    fmt_precip,
    fmt_temp,
    fmt_wind,
    geocode,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _resp(data, status=200):
    m = MagicMock()
    m.status_code = status
    m.json.return_value = data
    m.raise_for_status.return_value = None
    return m


def _http_error(status):
    m = MagicMock()
    m.status_code = status
    err = requests.HTTPError(response=m)
    m.raise_for_status.side_effect = err
    return m


# ---------------------------------------------------------------------------
# aggregate_daily
# ---------------------------------------------------------------------------

_RECORDS = [
    {
        "timestamp": "2024-07-15T10:00:00+02:00",
        "temperature": 20.0, "precipitation": 0.5,
        "wind_speed": 10.0, "wind_direction": 90,
        "relative_humidity": 70, "sunshine": 30,
        "icon": "partly-cloudy-day", "condition": "dry",
    },
    {
        "timestamp": "2024-07-15T14:00:00+02:00",
        "temperature": 25.0, "precipitation": 1.5,
        "wind_speed": 20.0, "wind_direction": 180,
        "relative_humidity": 60, "sunshine": 60,
        "icon": "clear-day", "condition": "dry",
    },
    {
        "timestamp": "2024-07-16T10:00:00+02:00",
        "temperature": 18.0, "precipitation": 3.0,
        "wind_speed": 25.0, "wind_direction": 270,
        "relative_humidity": 80, "sunshine": 0,
        "icon": "rain", "condition": "rain",
    },
]


def test_aggregate_daily_basic():
    result = aggregate_daily(_RECORDS)
    assert len(result) == 2
    day = result[0]
    assert day["date"] == "2024-07-15"
    assert day["temp_min"] == 20.0
    assert day["temp_max"] == 25.0
    assert day["temp_avg"] == pytest.approx(22.5)
    assert day["precip_total"] == pytest.approx(2.0)
    assert day["wind_avg"] == pytest.approx(15.0)
    assert day["sunshine_total"] == 90


def test_aggregate_daily_second_day():
    result = aggregate_daily(_RECORDS)
    day = result[1]
    assert day["date"] == "2024-07-16"
    assert day["temp_min"] == day["temp_max"] == 18.0


def test_aggregate_daily_empty():
    assert aggregate_daily([]) == []


def test_aggregate_daily_missing_fields():
    records = [{
        "timestamp": "2024-07-15T10:00:00",
        "temperature": None, "precipitation": None,
        "wind_speed": None, "relative_humidity": None,
        "sunshine": None, "icon": None, "condition": None,
    }]
    result = aggregate_daily(records)
    assert len(result) == 1
    day = result[0]
    assert day["temp_min"] is None
    assert day["temp_max"] is None
    assert day["precip_total"] is None
    assert day["wind_avg"] is None


def test_aggregate_daily_sorted_by_date():
    records = [
        {"timestamp": "2024-07-17T10:00:00", "temperature": 20.0, "precipitation": 0.0,
         "wind_speed": 10.0, "relative_humidity": 60, "sunshine": 30,
         "icon": "clear-day", "condition": "dry"},
        {"timestamp": "2024-07-15T10:00:00", "temperature": 22.0, "precipitation": 0.0,
         "wind_speed": 10.0, "relative_humidity": 60, "sunshine": 30,
         "icon": "clear-day", "condition": "dry"},
    ]
    result = aggregate_daily(records)
    assert result[0]["date"] == "2024-07-15"
    assert result[1]["date"] == "2024-07-17"


# ---------------------------------------------------------------------------
# Formatter functions
# ---------------------------------------------------------------------------

def test_fmt_temp_dwd():
    assert fmt_temp(22.5) == "22.5 °C"
    assert fmt_temp(22.5, "dwd") == "22.5 °C"


def test_fmt_temp_si():
    assert fmt_temp(295.6, "si") == "295.6 K"


def test_fmt_temp_none():
    assert fmt_temp(None) == "–"


def test_fmt_wind_dwd():
    assert "km/h" in fmt_wind(15.0)


def test_fmt_wind_si():
    assert "m/s" in fmt_wind(5.0, units="si")


def test_fmt_wind_with_direction():
    result = fmt_wind(10.0, 270)
    assert "km/h" in result
    assert "W" in result


def test_fmt_wind_none():
    assert fmt_wind(None) == "–"


def test_fmt_precip_dwd():
    assert fmt_precip(2.5) == "2.5 mm"


def test_fmt_precip_si():
    assert fmt_precip(2.5, "si") == "2.5 kg/m²"


def test_fmt_precip_none():
    assert fmt_precip(None) == "–"


# ---------------------------------------------------------------------------
# geocode
# ---------------------------------------------------------------------------

_NOM = [{"lat": "48.137", "lon": "11.575", "display_name": "München, Bayern, Deutschland"}]


def test_geocode_success():
    with patch("requests.get", return_value=_resp(_NOM)):
        lat, lon, display = geocode("Munich")
    assert lat == pytest.approx(48.137)
    assert lon == pytest.approx(11.575)
    assert "München" in display


def test_geocode_cache_hit():
    with patch("requests.get", return_value=_resp(_NOM)) as mock_get:
        geocode("Munich")
        geocode("Munich")
    assert mock_get.call_count == 1


def test_geocode_cache_miss_different_location():
    with patch("requests.get", return_value=_resp(_NOM)) as mock_get:
        geocode("Munich")
        geocode("Berlin")
    assert mock_get.call_count == 2


def test_geocode_not_found():
    with patch("requests.get", return_value=_resp([])):
        with pytest.raises(SystemExit):
            geocode("NonExistentPlaceXYZ999")


def test_geocode_network_error():
    with patch("requests.get", side_effect=requests.ConnectionError("timeout")):
        with pytest.raises(SystemExit):
            geocode("Munich")


def test_geocode_json_decode_error():
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.side_effect = json.JSONDecodeError("", "", 0)
    with patch("requests.get", return_value=m):
        with pytest.raises(SystemExit):
            geocode("Munich")


# ---------------------------------------------------------------------------
# brightsky_get
# ---------------------------------------------------------------------------

_BS_DATA = {"weather": [{"temperature": 20.0}]}


def test_brightsky_get_success():
    with patch("requests.get", return_value=_resp(_BS_DATA)):
        result = brightsky_get("/weather", {"lat": 48.1, "lon": 11.6})
    assert result == _BS_DATA


def test_brightsky_404_exits():
    with patch("requests.get", return_value=_http_error(404)):
        with pytest.raises(SystemExit):
            brightsky_get("/weather", {"lat": 48.1, "lon": 11.6})


def test_brightsky_429_exits():
    with patch("requests.get", return_value=_http_error(429)):
        with pytest.raises(SystemExit):
            brightsky_get("/weather", {"lat": 48.1, "lon": 11.6})


def test_brightsky_5xx_exits():
    with patch("requests.get", return_value=_http_error(502)):
        with pytest.raises(SystemExit):
            brightsky_get("/weather", {"lat": 48.1, "lon": 11.6})


def test_brightsky_json_decode_error_exits():
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.side_effect = json.JSONDecodeError("", "", 0)
    with patch("requests.get", return_value=m):
        with pytest.raises(SystemExit):
            brightsky_get("/weather", {"lat": 48.1, "lon": 11.6})


def test_brightsky_optional_returns_none_on_http_error():
    with patch("requests.get", return_value=_http_error(404)):
        result = brightsky_get("/alerts", {"lat": 48.1, "lon": 11.6}, optional=True)
    assert result is None


def test_brightsky_optional_returns_none_on_json_error():
    m = MagicMock()
    m.raise_for_status.return_value = None
    m.json.side_effect = json.JSONDecodeError("", "", 0)
    with patch("requests.get", return_value=m):
        result = brightsky_get("/weather", {"lat": 48.1, "lon": 11.6}, optional=True)
    assert result is None


def test_brightsky_optional_returns_none_on_network_error():
    with patch("requests.get", side_effect=requests.ConnectionError("timeout")):
        result = brightsky_get("/weather", {"lat": 48.1, "lon": 11.6}, optional=True)
    assert result is None
