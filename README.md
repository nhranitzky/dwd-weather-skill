# DWD Weather CLI

A command-line weather tool powered by the [BrightSky API](https://brightsky.dev),
which provides free access to data from the **Deutscher Wetterdienst (DWD)** –
Germany's national meteorological service.

Features include current observations, multi-day forecasts, historical queries,
weather alerts, and station discovery – all by city name, with no API key required.

---

## Requirements

| Tool | Version | Install |
|------|---------|---------|
| [uv](https://docs.astral.sh/uv/) | ≥ 0.4 | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Python | ≥ 3.11 | managed automatically by `uv` |

> **Note:** `uv` installs and manages Python for you if needed. You do not need
> to install Python separately.

---

## Installation

### Standalone (local use)

#### 1 – Clone or download

```bash
git clone https://github.com/your-org/dwd-weather-skill.git
cd dwd-weather-skill
```

#### 2 – Install dependencies

```bash
make install
```

This runs `uv sync` inside `dwd-weather/`, creating a `.venv/` with all
dependencies (`requests`, `rich`, `click`).



#### 3 – Make the launcher executable

```bash
chmod +x dwd-weather/bin/weather
```

#### 4 – (Optional) Add to PATH

To call `weather` from anywhere:

```bash
# Option A: symlink into a directory already in PATH
ln -s "$(pwd)/dwd-weather/bin/weather" ~/.local/bin/weather

# Option B: add the bin/ directory to PATH in your shell config
echo 'export PATH="$PATH:'"$(pwd)/dwd-weather/bin"'"' >> ~/.bashrc
source ~/.bashrc
```

#### 5 – Run

```bash
weather current Munich
weather forecast Berlin --days 7 --daily
weather summary Hamburg
```

---

### Openclaw Skill Installation

#### 1 – Build the skill package

```bash
make package
```

This produces `dwd-weather.skill_v<version>.zip` in the repo root.

#### 2 – Deploy to the Openclaw device

```bash
make deploy   # scp the zip to pi@openclaw.local
```

Or manually copy the zip to the device and unpack it into the Openclaw skills
directory, then run the install script inside the unpacked folder:

```bash
cd /path/to/unpacked/dwd-weather
bash install-skill.sh
```

`install-skill.sh` runs `uv sync --no-dev` and sets the executable bit on
`bin/weather`. Openclaw will invoke the skill via `{baseDir}/bin/weather`.

---

## Usage

All commands accept a location as free-form text (city name, address, etc.).
Geocoding is handled automatically via OpenStreetMap.

### Current Weather

```bash
weather current Munich
weather current "Frankfurt am Main"
weather current Sylt --units si
```

### Forecast

```bash
# Hourly forecast for the next 3 days (default)
weather forecast Berlin

# 7-day daily summary
weather forecast Hamburg --days 7 --daily
```

### Historical Weather

```bash
# Single day (hourly)
weather history Cologne --date 2024-07-15

# Date range with daily summary
weather history Dresden --date 2023-06-01 --end-date 2023-06-30 --daily

# Historical data with SI units
weather history Munich --date 2020-01-01 --end-date 2020-03-31 --daily --units si
```

### Weather Alerts

```bash
# Active DWD warnings (Germany only)
weather alerts Stuttgart
weather alerts "Berchtesgadener Land"
```

### Nearby Stations

```bash
# Stations within 50 km (default)
weather stations Nuremberg

# Closer radius, show more results
weather stations Bremen --radius 25 --limit 20
```

### At-a-Glance Summary

```bash
# Current conditions + 5-day daily outlook + alerts
weather summary Freiburg

# Extend to 10-day outlook
weather summary Kiel --days 10
```

### Global Options

```bash
weather --help              # Show all commands
weather forecast --help     # Help for a specific command
weather current Berlin --tz UTC --units si
```

---

## Running Without Adding to PATH

Use `uv run` directly from inside the `dwd-weather/` folder:

```bash
cd dwd-weather
uv run python -m scripts.main current Munich
uv run python -m scripts.main summary Berlin --days 7
```

---

## Project Structure

```
dwd-weather-skill/
├── Makefile                  ← dev tasks: install, lint, package, deploy
├── README.md                 ← this file
└── dwd-weather/
    ├── SKILL.md              ← Openclaw skill manifest
    ├── install-skill.sh      ← on-device setup script
    ├── pyproject.toml        ← Python project / uv configuration
    ├── bin/
    │   └── weather           ← shell launcher script
    └── scripts/
        ├── __init__.py
        ├── main.py           ← CLI entry point (Click)
        ├── utils.py          ← shared utilities
        ├── cmd_current.py    ← `weather current`
        ├── cmd_forecast.py   ← `weather forecast`
        ├── cmd_history.py    ← `weather history`
        ├── cmd_alerts.py     ← `weather alerts`
        ├── cmd_stations.py   ← `weather stations`
        └── cmd_summary.py    ← `weather summary`
```

---

## Data Sources & Attribution

All data is sourced from the **Deutscher Wetterdienst (DWD)** via BrightSky:

- **Current weather / SYNOP** – DWD station network (updated every 30 min)
- **Forecast** – DWD MOSMIX model (up to 240 h ahead)
- **Historical** – DWD Climate Data Center (CDC), going back decades
- **Alerts** – DWD CAP (Common Alerting Protocol) warnings
- **Geocoding** – OpenStreetMap Nominatim (© OpenStreetMap contributors)

The [DWD Terms of Use](https://www.dwd.de/EN/service/copyright/copyright_artikel.html) apply to all retrieved data.
BrightSky is free to use and open-source ([MIT License](https://github.com/jdemaeyer/brightsky/blob/master/LICENSE)).

---

## BrightSky API Endpoints Used

| Endpoint | Purpose |
|----------|---------|
| `GET /current_weather` | Latest consolidated SYNOP observation |
| `GET /weather` | Hourly weather (historical + forecast via MOSMIX) |
| `GET /alerts` | Active CAP weather warnings from DWD |
| `GET /sources` | Nearby DWD station discovery |

All endpoints accept `lat`/`lon`. No authentication required.

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| `command not found: weather` | Check PATH setup or use full path `./dwd-weather/bin/weather` |
| `Location not found` | Try a more specific name or include the country (e.g. `"Munich, Germany"`) |
| `No alert data` | Alerts are only available for locations within Germany |
| `No historical data` | Not all stations have long historical records; try `weather stations` to check coverage |
| Network errors | BrightSky requires internet access; check connectivity |

---

## Adding New Features

- Add a new `scripts/cmd_<name>.py` with a `@click.command()` function.
- Register it in `scripts/main.py` with `cli.add_command(...)`.
- Use helpers from `scripts/utils.py` for geocoding, API calls, and formatting.
- Available extra BrightSky endpoints: `/radar` (precipitation radar), `/synop` (raw SYNOP).

---

## Development Notes
Parts of this codebase were generated or assisted by Claude Code  Sonnet 4.6  
All generated code has been reviewed and tested by human developers.

## License

MIT – see [BrightSky license](https://github.com/jdemaeyer/brightsky/blob/master/LICENSE).
DWD data is subject to the DWD Terms of Use.
