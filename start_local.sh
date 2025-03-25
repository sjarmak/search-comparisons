#!/bin/bash

# Script to start both frontend and backend development servers

# Set environment to local
export APP_ENVIRONMENT=local
export DEBUG=true

# Load local environment variables if .env.local exists
if [ -f .env.local ]; then
  echo "Loading environment variables from .env.local"
  set -a
  source .env.local
  set +a
else
  echo "Warning: .env.local not found, using default environment"
fi

# Start backend in background
echo "Starting backend server..."
cd backend
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &
BACKEND_PID=$!
cd ..

# Give backend time to start
sleep 2

# Start frontend in foreground 
echo "Starting frontend server..."
cd frontend
npm start &
FRONTEND_PID=$!
cd ..

# Function to handle exit
function cleanup {
  echo "Shutting down servers..."
  kill $BACKEND_PID
  kill $FRONTEND_PID
  exit 0
}

# Register cleanup function on SIGINT (Ctrl+C)
trap cleanup SIGINT

# Keep script running
echo "Servers are running. Press Ctrl+C to stop."
wait 