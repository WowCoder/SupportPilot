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
    echo ""
    echo "  Backend:  http://localhost:5050"
    echo ""

    # Check if frontend dev server should be started
    FRONTEND_FLAG=""
    if [ "$1" = "--with-frontend" ] || [ "$1" = "-f" ]; then
        if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
            echo "  Frontend: http://localhost:5173"
            echo ""
            cd frontend && npm run dev &
            FRONTEND_PID=$!
            cd ..
        else
            echo "  (Frontend not found — skipping)"
        fi
    else
        echo "  (Add -f or --with-frontend to also start Vue dev server)"
        echo ""
    fi

    # Trap to clean up frontend on exit
    trap "kill $FRONTEND_PID 2>/dev/null" EXIT

    python -m flask --app wsgi:app run --debug --port 5050
fi
