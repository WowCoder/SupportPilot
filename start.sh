#!/bin/bash

# SupportPilot startup script

# 激活虚拟环境
cd "$(dirname "$0")"
source venv/bin/activate

# Check if .env file exists
if [ ! -f .env ]; then
    echo "Warning: .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "Please edit .env file with your configuration before running the application."
    exit 1
fi

# Check if logs directory exists
mkdir -p logs

# Check if running in production mode
if [ "$FLASK_ENV" = "production" ]; then
    echo "Starting SupportPilot in production mode with Gunicorn..."

    # Check if gunicorn is installed
    if ! command -v gunicorn &> /dev/null; then
        echo "Error: gunicorn is not installed. Run: pip install gunicorn"
        exit 1
    fi

    gunicorn -c gunicorn_config.py wsgi:app
else
    echo "Starting SupportPilot in development mode..."
    python -m flask --app wsgi:app run --debug
fi
