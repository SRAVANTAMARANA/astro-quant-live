#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(pwd)"

echo
echo "### ASTRO-QUANT: Create .env, start docker stack and run quick tests"
echo "Run this in the repository root where docker-compose.yml lives."
echo

read -p "Proceed? (y/N): " proceed
if [[ "${proceed,,}" != "y" ]]; then
  echo "Aborted."
  exit 1
fi

# Prompt for keys (you will paste them)
echo
echo "Paste values when prompted. If you want to leave any blank, press Enter."
read -p "ALPHAVANTAGE_API_KEY: " ALPHAVANTAGE_API_KEY
read -p "TWELVEDATA_API_KEY: " TWELVEDATA_API_KEY
read -p "FINNHUB_API_KEY: " FINNHUB_API_KEY
read -p "TELEGRAM_BOT_TOKEN: " TELEGRAM_BOT_TOKEN
read -p "TELEGRAM_CHAT_ID: " TELEGRAM_CHAT_ID
read -p "OTHER_API_KEY (optional): " OTHER_API_KEY

# Create .env safely
ENV_FILE=".env"
if [[ -f "$ENV_FILE" ]]; then
  echo "Note: $ENV_FILE already exists. Backing it up to ${ENV_FILE}.bak"
  cp "$ENV_FILE" "${ENV_FILE}.bak"
fi

cat > "$ENV_FILE" <<EOF
# AstroQuant environment variables
ALPHAVANTAGE_API_KEY=${ALPHAVANTAGE_API_KEY}
TWELVEDATA_API_KEY=${TWELVEDATA_API_KEY}
FINNHUB_API_KEY=${FINNHUB_API_KEY}
TELEGRAM_BOT_TOKEN=${TELEGRAM_BOT_TOKEN}
TELEGRAM_CHAT_ID=${TELEGRAM_CHAT_ID}
OTHER_API_KEY=${OTHER_API_KEY}
# Add further vars below as needed (example: DATABASE_URL=...)
EOF

chmod 600 "$ENV_FILE"
echo ".env created and protected (chmod 600)."

# Ensure .env is in .gitignore
if ! grep -q "^\.env$" .gitignore 2>/dev/null; then
  echo ".env" >> .gitignore
  echo "Added .env to .gitignore"
fi

# Ensure we're in folder with docker-compose.yml
if [[ ! -f "docker-compose.yml" && ! -f "docker-compose.yaml" ]]; then
  echo "ERROR: docker-compose.yml not found in $(pwd)."
  echo "Please cd to the repo root (where docker-compose.yml lives) and re-run this script."
  exit 2
fi

# Start docker
echo
echo "Starting docker-compose (build + detached)..."
docker-compose down || true
docker-compose up --build -d

echo
echo "Waiting 6s for containers to initialise..."
sleep 6

# Show containers
echo
echo "=== docker ps ==="
docker ps --format "table {{.Names}}\t{{.Image}}\t{{.Status}}\t{{.Ports}}"

# Quick HTTP tests (adjust ports if your compose maps different ports)
BACKEND_HOST="localhost"
BACKEND_PORT="8000"
FRONTEND_PORT="3000"

echo
echo "Running quick health checks..."
echo "Backend health: http://${BACKEND_HOST}:${BACKEND_PORT}/health"
curl -s -S --max-time 5 "http://${BACKEND_HOST}:${BACKEND_PORT}/health" || echo "Backend /health request failed (connection refused or timeout)"

echo
echo "Docs openapi (backend): http://${BACKEND_HOST}:${BACKEND_PORT}/docs"
echo "Frontend (if any): http://localhost:${FRONTEND_PORT}/"
echo

# Optional test: Telegram message via backend endpoint (if backend exposes /send_custom_message)
read -p "Send a test Telegram message through backend endpoint? (y/N): " SENDTG
if [[ "${SENDTG,,}" == "y" ]]; then
  # Compose a minimal JSON payload - backend must expose /send_custom_message endpoint
  read -p "Enter message text to send (default: 'Hello from local test'): " MSG
  MSG="${MSG:-Hello from local test}"
  echo "Sending via backend..."
  curl -s -X POST "http://${BACKEND_HOST}:${BACKEND_PORT}/send_custom_message" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"${MSG}\"}" \
    || echo "Failed to hit /send_custom_message (endpoint may be different)."
fi

echo
echo "If any connection refused messages occur, check container logs:"
echo "  docker-compose logs backend"
echo "  docker-compose logs frontend"
echo
echo "To open an interactive shell in the backend container:"
echo "  docker-compose exec backend /bin/sh   (or /bin/bash if available)"
echo
echo "Script finished."
