# backend/server.py
import os
import logging
from typing import Optional, Any, Dict

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="AstroQuant Backend")

# CORS - for dev use "*"; in prod set to your frontend URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# environment variables (set these in Render's Environment)
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"

def send_telegram_message(text: str, parse_mode: str = "HTML", timeout: int = 15) -> Dict[str, Any]:
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram config missing (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)")
    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": parse_mode}
    resp = requests.post(url, json=payload, timeout=timeout)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"Telegram returned non-json: {resp.text[:200]}")
    if not resp.ok or not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data

class NotifyRequest(BaseModel):
    text: str
    parse_mode: Optional[str] = "HTML"

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/notify")
async def notify(req: NotifyRequest):
    try:
        res = send_telegram_message(req.text, req.parse_mode)
    except Exception as e:
        logger.exception("Telegram send failed")
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "telegram": res}

# Minimal signal endpoints for your ICT front-end
class SignalPayload(BaseModel):
    model: str
    symbol: str
    timeframe: str
    direction: Optional[str] = None
    price: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

# In-memory stats (resets on restart)
STATS = {"total": 0, "by_model": {}, "signals": []}
MAX_SIGNALS = 500

def record_signal(p: SignalPayload):
    STATS["total"] += 1
    m = p.model.upper()
    STATS["by_model"].setdefault(m, 0)
    STATS["by_model"][m] += 1
    rec = {"ts": datetime.utcnow().isoformat(), "model": m, "symbol": p.symbol, "tf": p.timeframe, "dir": p.direction, "price": p.price}
    STATS["signals"].insert(0, rec)
    if len(STATS["signals"]) > MAX_SIGNALS:
        STATS["signals"].pop()

@app.post("/signal")
async def signal(p: SignalPayload):
    record_signal(p)
    return {"ok": True, "stats": {"total": STATS["total"], "by_model": STATS["by_model"]}}

@app.get("/stats")
async def stats():
    return {"ok": True, "stats": STATS}

# run with: uvicorn server:app --host 0.0.0.0 --port $PORT
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("server:app", host="0.0.0.0", port=int(os.getenv("PORT", 8000)))
