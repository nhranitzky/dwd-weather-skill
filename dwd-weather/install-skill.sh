#!/bin/bash

# sync the virtual environment dependencies first
echo "Installing dependencies with uv sync..."
uv sync --no-dev
echo "Set execute permissions for bin/weather..."
chmod +x bin/weather
