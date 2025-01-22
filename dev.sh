#!/bin/bash

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Export environment variables
export FLASK_ENV=development
export FLASK_APP=server:app

# Start Flask application
flask run --host=0.0.0.0 --port=8000