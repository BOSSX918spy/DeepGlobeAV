#!/bin/bash

echo "Starting DeepGlobeAV+ Command System..."

PROJECT_DIR="$(pwd)"
IP=$(hostname -I | awk '{print $1}')

# Function to kill all background jobs on exit
cleanup() {
    echo ""
    echo "Stopping all services..."
    kill 0
}
trap cleanup EXIT

# ======================
# BACKEND
# ======================
echo "Launching backend..."
cd "$PROJECT_DIR/dashboard/backend"
python3 server.py > backend.log 2>&1 &

BACKEND_PID=$!

# ======================
# FRONTEND
# ======================
echo "Launching frontend..."
cd "$PROJECT_DIR/dashboard/frontend"
python3 -m http.server 9000 --bind 0.0.0.0 > frontend.log 2>&1 &

FRONTEND_PID=$!

sleep 2

echo ""
echo "System Started."
echo ""
echo "Backend API:   http://$IP:5000"
echo "Dashboard UI:  http://$IP:9000"
echo ""
echo "Logs:"
echo "Backend:  dashboard/backend/backend.log"
echo "Frontend: dashboard/frontend/frontend.log"
echo ""
echo "Press CTRL+C to stop."

# Wait forever
wait