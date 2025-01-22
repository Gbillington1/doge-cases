#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Export environment variables
export FLASK_ENV=production
export FLASK_APP=server:app

# Create logs directory if it doesn't exist
mkdir -p logs

# Start Gunicorn
gunicorn \
    --bind 0.0.0.0:8000 \
    --workers 3 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log \
    --capture-output \
    --log-level info \
    server:app 