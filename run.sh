#!/usr/bin/env bash
set -euo pipefail

VENV_PATH="./venv"
BACKEND_MODULE="backend.server:app"
BACKEND_PORT=8000
FRONTEND_DIR="./frontend"

if [ ! -f "$VENV_PATH/bin/activate" ]; then
  echo "ERROR: venv not found at $VENV_PATH - create it first: python3 -m venv venv"
  exit 1
fi

echo "Activating venv..."
source "$VENV_PATH/bin/activate"

echo "Starting backend (uvicorn) on 0.0.0.0:$BACKEND_PORT ..."
nohup python -m uvicorn $BACKEND_MODULE --host 0.0.0.0 --port $BACKEND_PORT --reload > backend.log 2>&1 &

if [ -d "$FRONTEND_DIR" ]; then
  echo "Starting frontend in $FRONTEND_DIR ..."
  cd "$FRONTEND_DIR"
  if [ ! -d "node_modules" ]; then
    echo "Installing frontend deps..."
    npm install
  fi
  nohup npm run dev > ../frontend.log 2>&1 &
  cd -
else
  echo "No frontend dir ($FRONTEND_DIR) found - skipping frontend."
fi

sleep 1
echo "Backend should be at http://127.0.0.1:$BACKEND_PORT/docs"
echo "Logs: backend.log and frontend.log"
