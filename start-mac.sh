#!/bin/bash
set -e

echo "========================================"
echo "Bain Productivity Tool - Mac/Linux Startup"
echo "========================================"

# Create demo-docs folder if it doesn't exist
if [ ! -d "demo-docs" ]; then
    echo "Creating demo-docs folder..."
    mkdir -p demo-docs
fi

# Copy .env if it doesn't exist
if [ ! -f "backend/.env" ] && [ -f ".env.example" ]; then
    echo "Copying .env.example to backend/.env..."
    cp .env.example backend/.env
fi

# Start backend
echo ""
echo "Starting backend..."
cd backend
python3 -m venv venv 2>/dev/null || true
source venv/bin/activate
pip install -r requirements.txt --quiet
uvicorn app.main:app --reload --port 8000 &
BACKEND_PID=$!
cd ..

# Wait for backend
echo "Waiting for backend to start..."
sleep 3

# Start frontend
echo ""
echo "Starting frontend..."
cd frontend
npm install --silent
npm run dev &
FRONTEND_PID=$!
cd ..

# Wait and open browser
sleep 3
if command -v open &> /dev/null; then
    open http://localhost:5173
elif command -v xdg-open &> /dev/null; then
    xdg-open http://localhost:5173
fi

echo ""
echo "========================================"
echo "Servers running:"
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:5173"
echo "API Docs: http://localhost:8000/docs"
echo ""
echo "Press Ctrl+C to stop all servers"
echo "========================================"

# Trap Ctrl+C to kill both processes
trap "kill $BACKEND_PID $FRONTEND_PID 2>/dev/null" EXIT
wait
