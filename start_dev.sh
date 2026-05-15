#!/bin/bash

echo "Starting Backend and Frontend in integrated terminal..."

# Function to stop both processes on Ctrl+C
cleanup() {
    echo "Stopping services..."
    kill $(jobs -p)
    exit
}

trap cleanup SIGINT

# Start Backend
(cd backend && uvicorn main:app --reload --port 8000) &

# Start Frontend
(cd frontend && npm run dev) &

# Wait for both
wait
