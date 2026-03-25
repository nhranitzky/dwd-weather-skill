---
name: dwd-weather
description:  Query DWD (Deutscher Wetterdienst) weather data . Use this skill whenever the user asks about weather data from DWD, wants to look up current conditions, forecast, historical weather, weather alerts, or nearby weather stations for any German city or location. Also trigger when the user mentions BrightSky, DWD, SYNOP,  MOSMIX, German weather data, or wants to run weather CLI scripts.Covers  current weather, multi-day forecast, historical queries,weather warnings/alerts, and station discovery – all by city name.
metadata: { "openclaw": {"emoji": "🌤️"} }
---

# DWD Weather Skill

Query DWD weather data via the **BrightSky API** (`api.brightsky.dev`).


## Available Commands

| Command | Description |
|---------|-------------|
| `{baseDir}/bin/weather current <location>` | Current SYNOP observation (temperature, wind, humidity, …) |
| `{baseDir}/bin/weather forecast <location>` | Hourly MOSMIX forecast up to 10 days |
| `{baseDir}/bin/weather forecast <location> --daily` | Condensed daily forecast |
| `{baseDir}/bin/weather history <location> --date YYYY-MM-DD` | Historical hourly observations |
| `{baseDir}/bin/weather history … --end-date YYYY-MM-DD --daily` | Historical daily summary over a range |
| `{baseDir}/bin/weather alerts <location>` | Active DWD weather warnings (Germany only) |
| `{baseDir}/bin/weather stations <location>` | Nearby DWD observation stations + data coverage |
| `{baseDir}/bin/weather summary <location>` | At-a-glance: current + multi-day outlook + alerts |

## Key Options

- `--days N` — forecast/summary horizon (1–10, default 3 or 5)
- `--daily` — aggregate hourly rows into daily summaries
- `--date / --end-date` — historical date range (YYYY-MM-DD)
- `--radius KM` — station search radius in km, 1–1000 (default 50)
- `--tz TZ` — IANA timezone (default `Europe/Berlin`)
- `--units dwd|si` — unit system (DWD: km/h, mm, °C; SI: m/s, kg/m², K)
- `--json` — output data as JSON instead of a formatted table

## How Openclaw Should Use This Skill

1. **Identify the query type** — current / forecast / historical / alerts / stations / summary.
2. **Extract location** from the user's message.
3. **Run the appropriate script** using `{baseDir}/bin/weather` with `--json`.
4. **Pass extra flags** based on user intent (date ranges, `--daily`, etc.).
5. **Parse the JSON output** and present the relevant figures to the user.

### Example invocations

```bash
# Current weather
{baseDir}/bin/weather current Munich --json

# 7-day daily forecast
{baseDir}/bin/weather forecast Hamburg --days 7 --daily --json

# Historical: all of January 2024, daily summary
{baseDir}/bin/weather history Berlin --date 2024-01-01 --end-date 2024-01-31 --daily --json

# Active weather warnings
{baseDir}/bin/weather alerts Cologne --json

# Nearby stations within 30 km
{baseDir}/bin/weather stations Frankfurt --radius 30 --json

# Quick summary (current + 5-day outlook)
{baseDir}/bin/weather summary Stuttgart --json
```

## JSON Output Reference

### `current --json`

```json
{
  "location": "München, Bayern, Deutschland",
  "weather": {
    "timestamp": "2024-07-15T14:00:00+02:00",
    "temperature": 28.4,
    "dew_point": 12.1,
    "relative_humidity": 38,
    "wind_speed": 15.0,
    "wind_direction": 270,
    "wind_gust_speed": 28.0,
    "wind_gust_direction": 280,
    "precipitation_10": 0.0,
    "cloud_cover": 25,
    "pressure_msl": 1018.3,
    "visibility": 40000,
    "sunshine_30": 28,
    "condition": "dry",
    "icon": "clear-day"
  },
  "source": {
    "station_name": "MÜNCHEN-FLUGHAFEN",
    "dwd_station_id": "01262",
    "distance": 28500,
    "height": 446
  }
}
```

### `forecast --json` (hourly)

```json
{
  "location": "Hamburg, Deutschland",
  "source": "HAMBURG-FUHLSBÜTTEL",
  "mode": "hourly",
  "records": [
    {
      "timestamp": "2024-07-15T12:00:00+02:00",
      "temperature": 22.1,
      "precipitation": 0.0,
      "wind_speed": 18.0,
      "wind_direction": 240,
      "relative_humidity": 55,
      "pressure_msl": 1015.2,
      "visibility": 35000,
      "sunshine": 45,
      "condition": "dry",
      "icon": "partly-cloudy-day"
    }
  ]
}
```

### `forecast --daily --json`

```json
{
  "location": "Hamburg, Deutschland",
  "source": "HAMBURG-FUHLSBÜTTEL",
  "mode": "daily",
  "records": [
    {
      "date": "2024-07-15",
      "temp_min": 16.2,
      "temp_max": 24.8,
      "temp_avg": 20.1,
      "precip_total": 0.0,
      "wind_avg": 17.5,
      "humidity_avg": 58.3,
      "sunshine_total": 420,
      "icon": "⛅"
    }
  ]
}
```

### `history --json`

Same structure as `forecast --json`. Additionally contains `period`, `stations`, and `observation_types`:

```json
{
  "location": "Berlin, Deutschland",
  "period": "2024-01-01 → 2024-01-31",
  "stations": ["BERLIN-TEMPELHOF"],
  "observation_types": ["historical"],
  "mode": "daily",
  "records": [...]
}
```

### `alerts --json`

```json
{
  "location": "Köln, Nordrhein-Westfalen, Deutschland",
  "municipality": "Köln",
  "warn_cell_id": "105315000",
  "alerts": [
    {
      "event": "WIND",
      "severity": "moderate",
      "headline": "Amtliche WARNUNG vor WIND",
      "description": "Windböen bis 60 km/h erwartet.",
      "instruction": "Lose Gegenstände sichern.",
      "onset": "2024-07-15T18:00:00+02:00",
      "expires": "2024-07-16T06:00:00+02:00"
    }
  ]
}
```

`alerts` is an empty list when no active warnings exist. `warn_cell_id` is empty for locations outside Germany.

### `stations --json`

```json
{
  "location": "Frankfurt am Main, Hessen, Deutschland",
  "radius_km": 30,
  "stations": [
    {
      "station_name": "FRANKFURT/MAIN",
      "dwd_station_id": "01420",
      "observation_type": "historical",
      "distance": 5800,
      "height": 112,
      "first_record": "1949-01-01T00:00:00+00:00",
      "last_record": "2024-07-14T23:00:00+00:00",
      "lat": 50.0527,
      "lon": 8.5696
    }
  ]
}
```

### `summary --json`

```json
{
  "location": "Stuttgart, Baden-Württemberg, Deutschland",
  "current": { },
  "current_source": { },
  "forecast": [
    {
      "date": "2024-07-15",
      "temp_min": 18.0,
      "temp_max": 32.5,
      "precip_total": 0.0,
      "wind_avg": 12.3,
      "sunshine_total": 510,
      "icon": "☀️"
    }
  ],
  "alerts": []
}
```

`current` and `current_source` have the same structure as in `current --json`. `forecast` is a list of daily aggregates. `alerts` is a list of active warnings (empty if none).

## Troubleshooting

| Error | Cause | Resolution |
|-------|-------|-----------|
| `Location not found` | OSM Nominatim could not resolve the place name | Try a more specific name, add country (e.g. `Berlin, Germany`) |
| `BrightSky API error: No data for this location` | 404 – no DWD station found near the coordinates | Try a German city closer to a DWD station |
| `BrightSky API error: Rate limit exceeded` | 429 – too many requests | Wait a moment and retry |
| `BrightSky API error: Service unavailable` | 5xx – BrightSky is temporarily down | Retry after a few minutes |
| `No forecast data available` | Location is outside BrightSky coverage | DWD data covers Germany and neighbouring regions; try a German city |
| `warn_cell_id` is empty | Location is outside Germany | DWD alerts only cover Germany; `alerts` will be an empty list |
| `No historical data found` | Station has no data for the requested period | Try a shorter range or a different location |
