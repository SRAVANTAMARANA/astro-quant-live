#!/usr/bin/env bash
set -euo pipefail

print(){ echo -e "\n>>> $*\n"; }

# --- Git identity ---
git config user.name "SRAVANTAMARANA"
git config user.email "sravan.tamarana@gmail.com"

print "Git identity set as: $(git config user.name) <$(git config user.email)>"

# --- Ask repo + PAT ---
read -p "Enter your GitHub repo (e.g. SRAVANTAMARANA/astro-quant-live): " GH_REPO
read -s -p "Paste your GitHub PAT (input hidden): " GITHUB_PAT
echo

# --- Ask API keys ---
echo "Enter API keys (paste each then ENTER):"
read -p "Twelvedata API key: " TWELVEDATA_API_KEY
read -p "Finnhub API key: " FINNHUB_API_KEY
read -p "Alphavantage API key: " ALPHAVANTAGE_API_KEY
read -p "Telegram Bot Token: " TELEGRAM_BOT_TOKEN
read -p "Telegram Chat ID: " TELEGRAM_CHAT_ID

# --- Write .env ---
cat > .env <<ENV
TWELVEDATA_API_KEY=$TWELVEDATA_API_KEY
FINNHUB_API_KEY=$FINNHUB_API_KEY
ALPHAVANTAGE_API_KEY=$ALPHAVANTAGE_API_KEY

TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN
TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID

SCHEDULE_ENABLE=true
SCHEDULE_TZ=Asia/Kolkata
SCHEDULE_HOUR=9
SCHEDULE_MINUTE=0

BACKEND_HOST=0.0.0.0
BACKEND_PORT=8000
ENV

print ".env created with keys (ignored in git)."

# --- Structure ---
mkdir -p backend/app frontend Data Docs Utils backend/logs

# --- Backend main ---
cat > backend/app/main.py <<'PY'
from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
import os, requests, datetime, pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="AstroQuant Apex")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCHEDULE_ENABLE = os.getenv("SCHEDULE_ENABLE","true").lower() in ("1","true","yes")
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR","9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE","0"))
SCHEDULE_TZ = os.getenv("SCHEDULE_TZ","Asia/Kolkata")

def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"status":"no keys"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode":"HTML"}
    try:
        r = requests.post(url, json=payload, timeout=8)
        return {"status":"sent" if r.ok else "error", "http": r.status_code}
    except Exception as e:
        return {"status":"error", "error": str(e)}

class Signal(BaseModel):
    symbol: str
    signal: str
    strength: str
    note: str = ""

def demo_signals():
    return [
        {"symbol":"XAUUSD","signal":"BUY","strength":"high","note":"ICT momentum + astro confluence"},
        {"symbol":"EURUSD","signal":"SELL","strength":"medium","note":"mean reversion"}
    ]

def demo_news():
    now = datetime.datetime.utcnow().isoformat()+"Z"
    return [
        {"time": now, "headline":"Macro event impacts FX", "impact":"high"},
        {"time": now, "headline":"Planetary cycle confluence", "impact":"medium"}
    ]

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/signals", response_model=List[Signal])
def get_signals():
    sigs = demo_signals()
    text = "🔔 <b>AstroQuant Signals</b>\n" + "".join([f"{s['symbol']} → {s['signal']} ({s['strength']})\n" for s in sigs])
    send_to_telegram(text)
    return sigs

@app.get("/send_custom")
def send_custom(msg: str):
    return send_to_telegram(f"📝 <b>Custom Msg</b>: {msg}")

def build_brief():
    sigs = demo_signals()
    news = demo_news()
    ts = datetime.datetime.now(pytz.timezone(SCHEDULE_TZ)).strftime("%Y-%m-%d %H:%M %Z")
    text = f"📊 <b>AstroQuant Daily Brief</b>\n{ts}\n\n<b>Signals:</b>\n"
    text += "".join([f"• {s['symbol']}: {s['signal']} ({s['strength']})\n" for s in sigs])
    text += "\n<b>News:</b>\n" + "".join([f"• {n['headline']} ({n['impact']})\n" for n in news])
    return text

def daily_job():
    msg = build_brief()
    send_to_telegram(msg)

scheduler=None
@app.on_event("startup")
def start_scheduler():
    global scheduler
    if not SCHEDULE_ENABLE: return
    tz = pytz.timezone(SCHEDULE_TZ)
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(daily_job, CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone=tz))
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    global scheduler
    if scheduler: scheduler.shutdown(wait=False)
PY

# --- Backend Dockerfile ---
cat > backend/Dockerfile <<'DOCKER'
FROM python:3.10-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY . /app
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
DOCKER

# --- Backend requirements ---
cat > backend/requirements.txt <<'REQ'
fastapi
uvicorn[standard]
pydantic
requests
apscheduler
pytz
REQ

# --- Frontend ---
cat > frontend/index.html <<'HTML'
<!doctype html>
<html>
<head><meta charset="utf-8"><title>AstroQuant Apex</title></head>
<body>
  <h1>AstroQuant Apex Frontend</h1>
  <button onclick="loadSignals()">Load Signals</button>
  <pre id="out">Waiting...</pre>
<script>
async function loadSignals(){
  try{
    const r = await fetch("http://localhost:8000/signals");
    document.getElementById("out").innerText = JSON.stringify(await r.json(), null, 2);
  }catch(e){
    document.getElementById("out").innerText = "Error: "+e;
  }
}
</script>
</body>
</html>
HTML

cat > frontend/Dockerfile <<'DOCKER'
FROM python:3.10-slim
WORKDIR /app
COPY . /app
EXPOSE 3000
CMD ["python", "-m", "http.server", "3000", "--bind", "0.0.0.0"]
DOCKER

# --- docker-compose ---
cat > docker-compose.yml <<'YAML'
version: "3.9"
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    env_file: .env
    volumes: ["./backend:/app"]
    restart: unless-stopped
  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    volumes: ["./frontend:/app"]
    restart: unless-stopped
YAML

# --- .gitignore ---
cat > .gitignore <<'GITIGNORE'
venv/
node_modules/
__pycache__/
.env
*.pyc
*.log
GITIGNORE

# --- Commit & push ---
git add -A
git commit -m "AstroQuant Apex full push with Telegram + scheduler" || true
AUTH_URL="https://${GITHUB_PAT}@github.com/${GH_REPO}.git"
git remote remove origin 2>/dev/null || true
git remote add origin "$AUTH_URL"
git push -u origin main

# --- Run docker ---
read -p "Run docker-compose up -d --build now? (y/N) " ans
if [[ "$ans" =~ ^[Yy] ]]; then
  docker-compose up -d --build
  print "Backend: http://localhost:8000/  Frontend: http://localhost:3000/"
else
  print "Setup complete. Run: docker-compose up -d --build"
fi
