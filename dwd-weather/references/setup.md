# Setup Guide: dwd-weather-skill on Openclaw

## Skill Installation

The `dwd-weather.skill_v1.0.zip` was already unpacked in `~/.openclaw/skills/` or the workspace-specific skill folder.

The skill is in the folder `dwd-weather` – this is the working directory for all installation steps below.

### Install dependencies (optional)

```bash
uv sync --no-dev
```

### Make the launcher executable (normally already set)

```bash
chmod +x bin/weather
```

---

### Openclaw: check if the skill is ready and loaded

```bash
openclaw skills info dwd-weather
```

---

## Configuration

This skill requires **no API key** and no credentials. BrightSky is free and open to use.

