# backend/server.py
import os
import logging
from typing import Optional, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from datetime import datetime

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="AstroQuant Backend - ICT")

# Allowed origins - adjust in Render environment or set to '*' for testing
ALLOWED_ORIGINS = os.getenv("ALLOWED_ORIGINS", "*").split(",") if os.getenv("ALLOWED_ORIGINS") else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,  # e.g. https://your-frontend.onrender.com
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Environment names expected on Render / dev:
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"

def send_telegram_message(text: str, parse_mode: str = "HTML") -> Dict[str, Any]:
    """Send a telegram message. Raises RuntimeError on failure."""
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram bot token or chat id not configured in environment")
    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": parse_mode}
    resp = requests.post(url, json=payload, timeout=15)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"Telegram returned non-json: {resp.text}")
    if not resp.ok or not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data

class NotifyRequest(BaseModel):
    text: str

class SignalRequest(BaseModel):
    model: str               # e.g. "ICT", "GANN", "MATH", "MOMENTUM"
    symbol: str              # e.g. "AAPL"
    timeframe: str           # e.g. "1D", "15m"
    direction: Optional[str] = None  # "LONG" / "SHORT" / "NEUTRAL"
    price: Optional[float] = None
    meta: Optional[Dict[str, Any]] = None

# Simple in-memory stats for today (resets on process restart)
STATS = {
    "total_signals": 0,
    "by_model": {},         # model -> total count
    "by_model_success": {}, # model -> success count (manually reported)
    "signals": []           # list of recent signals (capped)
}
MAX_SIGNALS_STORED = 500

def record_signal(sig: SignalRequest):
    now = datetime.utcnow().isoformat()
    STATS["total_signals"] += 1
    m = sig.model.upper()
    STATS["by_model"].setdefault(m, 0)
    STATS["by_model"][m] += 1
    rec = {"ts": now, "model": m, "symbol": sig.symbol, "tf": sig.timeframe, "direction": sig.direction, "price": sig.price, "meta": sig.meta}
    STATS["signals"].insert(0, rec)
    if len(STATS["signals"]) > MAX_SIGNALS_STORED:
        STATS["signals"].pop()

@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}

@app.post("/notify")
async def notify(req: NotifyRequest):
    """Send Telegram message (for alerts & testing)."""
    try:
        data = send_telegram_message(req.text)
    except Exception as e:
        logger.exception("Telegram send failed")
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "telegram": data}

@app.post("/signal")
async def signal(req: SignalRequest):
    """
    Receive a signal from your model pipeline or front-end.
    Records it in-memory and optionally sends a Telegram note if env var set.
    """
    record_signal(req)
    # If TELEGRAM_NOTIFY env var set to "1", send a summary message
    if os.getenv("TELEGRAM_NOTIFY", "0") == "1":
        msg = f"<b>SIGNAL</b>\nModel: {req.model}\nSymbol: {req.symbol} {req.timeframe}\nDir: {req.direction}\nPrice: {req.price}"
        try:
            send_telegram_message(msg)
        except Exception as e:
            logger.warning("Telegram notify failed: %s", e)
    return {"ok": True, "stats": {"total_signals": STATS["total_signals"], "by_model": STATS["by_model"]}}

class SignalResultReport(BaseModel):
    model: str
    symbol: str
    timeframe: str
    outcome: str   # "WIN" or "LOSS" or "INVALID"
    notes: Optional[str] = None

@app.post("/report_result")
async def report_result(r: SignalResultReport):
    """Report whether a previously-recorded signal succeeded or failed (used for AI learning loop)."""
    m = r.model.upper()
    STATS["by_model_success"].setdefault(m, 0)
    if r.outcome.upper() == "WIN":
        STATS["by_model_success"][m] += 1
    return {"ok": True, "by_model_success": STATS["by_model_success"]}

@app.get("/stats")
async def stats():
    """Return aggregated stats for the day (in-memory)."""
    return {"ok": True, "stats": STATS}
