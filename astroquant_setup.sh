#!/bin/bash
echo "🚀 Setting up AstroQuant project..."

# Update system
sudo apt update && sudo apt upgrade -y

# Install dependencies
sudo apt install -y python3 python3-venv python3-pip nodejs npm git

# Create Python venv
python3 -m venv venv
source venv/bin/activate

# Install backend requirements
pip install fastapi uvicorn requests pandas numpy

# Install frontend requirements
cd frontend || exit
npm install
cd ..

# Run backend in background
nohup uvicorn backend.server:app --host 0.0.0.0 --port 8000 --reload > backend.log 2>&1 &

# Run frontend (React/HTML)
nohup npx serve frontend -l 3000 > frontend.log 2>&1 &

echo "✅ AstroQuant setup complete. Backend → http://localhost:8000  |  Frontend → http://localhost:3000"
