#!/bin/bash

echo "🧹 Cleaning up old processes..."
fuser -k 8090/tcp 2>/dev/null
pkill -f "next-dev" 2>/dev/null

echo "🔥 Starting AuditPRO Services (Compatibility Mode)..."

# Activate environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ venv not found! Run setup.sh first."
    exit 1
fi

# Start Backend
uvicorn main:app --host 0.0.0.0 --port 8090 & 
BACKEND_PID=$!

# Wait for backend
sleep 2

# Start Frontend using Webpack (Required for Termux/Android)
echo "🌐 Starting Frontend on port 3000 (using Webpack)..."
npx next dev -p 3000 --webpack &
FRONTEND_PID=$!

# Handle shutdown
trap "kill $BACKEND_PID $FRONTEND_PID; echo 'Stopping...'; exit" INT TERM
wait
