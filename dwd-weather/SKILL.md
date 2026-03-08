---
name: dwd-weather
description:  Query DWD (Deutscher Wetterdienst) weather data . Use this skill whenever the user asks about weather data from DWD, wants to look up current conditions, forecast, historical weather, weather alerts, or nearby weather stations for any German city or location. Also trigger when the user mentions BrightSky, DWD, SYNOP,  MOSMIX, German weather data, or wants to run weather CLI scripts.Covers  current weather, multi-day forecast, historical queries,weather warnings/alerts, and station discovery – all by city name.
metadata: { "openclaw": {"emoji": "🌤️"} }
---

# DWD Weather Skill

Query DWD weather data via the **BrightSky API** (`api.brightsky.dev`).
All scripts live in `scripts/`, are managed with `uv`, and launched via `{baseDir}/bin/weather`.

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
- `--radius KM` — station search radius (default 50 km)
- `--tz TZ` — IANA timezone (default `Europe/Berlin`)
- `--units dwd|si` — unit system (DWD: km/h, mm, °C; SI: m/s, kg/m², K)

## How Openclaw Should Use This Skill

1. **Identify the query type** — current / forecast / historical / alerts / stations / summary.
2. **Extract location** from the user's message.
3. **Run the appropriate script** using `{baseDir}/bin/weather`  
4. **Pass extra flags** based on user intent (date ranges, `--daily`, etc.).
5. **Present the output** — the scripts produce rich terminal tables; relay key figures to the user.

### Example invocations

```bash
# Current weather
{baseDir}/bin/weather current Munich

# 7-day daily forecast
{baseDir}/bin/weather forecast Hamburg --days 7 --daily

# Historical: all of January 2024, daily summary
{baseDir}/bin/weather history Berlin --date 2024-01-01 --end-date 2024-01-31 --daily

# Active weather warnings
{baseDir}/bin/weather alerts Cologne

# Nearby stations within 30 km
{baseDir}/bin/weather stations Frankfurt --radius 30

# Quick summary (current + 5-day outlook)
{baseDir}/bin/weather summary Stuttgart
```

