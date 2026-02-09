#!/bin/bash

# Start the validator UI
cd "$(dirname "$0")"

echo "🚀 Starting US Tariff Calculator Validator..."
echo ""
echo "Opening validator UI in your browser..."
echo "API: http://localhost:8000"
echo "UI: http://localhost:8080"
echo ""
echo "Press Ctrl+C to stop"
echo ""

# Start a simple HTTP server for the frontend
cd frontend
python3 -m http.server 8080 &
SERVER_PID=$!

# Wait a moment for server to start
sleep 2

# Open browser
open http://localhost:8080/validator.html

# Wait for user to press Ctrl+C
wait $SERVER_PID
