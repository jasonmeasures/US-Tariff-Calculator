#!/bin/bash

# US Tariff Calculator - Startup Script

echo "🇺🇸 US Tariff Calculator - Starting..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
if [ ! -f "venv/installed" ]; then
    echo "Installing dependencies..."
    pip install -q -r backend/requirements.txt
    touch venv/installed
fi

# Check if database exists
if [ ! -f "us_tariff_calculator.db" ]; then
    echo "Database not found. Running setup..."
    echo "This will load 79,338 HTS codes and 16,189 tariff overlays (~30 seconds)..."
    python backend/database_setup.py
fi

# Start API server
echo ""
echo "✅ Starting API server on http://localhost:8000"
echo "✅ Opening web interface..."
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Start API in background
python backend/api.py &
API_PID=$!

# Wait for API to start
sleep 2

# Open web interface
open frontend/index.html

# Wait for Ctrl+C
trap "kill $API_PID; exit" INT
wait $API_PID
