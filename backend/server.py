# backend/server.py
import os
import time
import logging
from typing import List, Dict, Any
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv

load_dotenv()  # loads .env from repo root

# Config from .env
TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY", "")
FINNHUB_API_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

SIGNAL_CACHE_TTL = int(os.getenv("SIGNAL_CACHE_TTL", "15"))  # seconds

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("astroquant-backend")

app = FastAPI(title="AstroQuant Backend - Signals")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production
    allow_methods=["*"],
    allow_headers=["*"],
)

# in-memory cache
_cache = {"signals": [], "ts": 0}


class Signal(BaseModel):
    symbol: str
    signal: str  # BUY/SELL/NONE
    strength: str  # high/medium/low
    source: str
    meta: Dict[str, Any] = {}


def fetch_from_twelvedata(symbol: str, interval="1min", outputsize=100):
    """Example: fetch latest candle from TwelveData"""
    if not TWELVEDATA_API_KEY:
        return None
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
        "apikey": TWELVEDATA_API_KEY,
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        logger.warning("TwelveData failed %s %s", r.status_code, r.text)
        return None
    return r.json()


def simple_signal_logic_from_data(symbol: str, data: dict) -> Signal:
    """
    Placeholder signal generator:
    - looks at last two close prices and returns BUY if last>prev, SELL if last<prev
    Replace with your ICT/Gann/math logic.
    """
    timeseries = data.get("values") or data.get("values", [])
    if not timeseries or len(timeseries) < 2:
        return Signal(symbol=symbol, signal="NONE", strength="low", source="data_missing")
    last = float(timeseries[0]["close"])
    prev = float(timeseries[1]["close"])
    if last > prev:
        s = "BUY"
        strength = "high" if (last - prev) / prev > 0.0005 else "medium"
    elif last < prev:
        s = "SELL"
        strength = "high" if (prev - last) / prev > 0.0005 else "medium"
    else:
        s = "NONE"
        strength = "low"
    return Signal(symbol=symbol, signal=s, strength=strength, source="twelvedata_simple")


def send_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        logger.debug("Telegram not configured")
        return False
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    try:
        r = requests.post(url, json=payload, timeout=10)
        r.raise_for_status()
        logger.info("Telegram sent")
        return True
    except Exception as e:
        logger.exception("Telegram send failed: %s", e)
        return False


def generate_signals_for_symbols(symbols: List[str]) -> List[Signal]:
    out: List[Signal] = []
    for s in symbols:
        # Try TwelveData, fallback to dummy
        data = fetch_from_twelvedata(s)
        if not data:
            # fallback dummy
            sig = Signal(symbol=s, signal="NONE", strength="low", source="fallback")
        else:
            sig = simple_signal_logic_from_data(s, data)
        out.append(sig)
    return out


@app.get("/signals", response_model=List[Signal])
def get_signals(background_tasks: BackgroundTasks):
    """Return cached signals. If cache expired, schedule a background refresh"""
    now = int(time.time())
    if now - _cache["ts"] > SIGNAL_CACHE_TTL:
        # update cache in background
        background_tasks.add_task(_refresh_cache)
    return _cache["signals"]


def _refresh_cache():
    """Fetch fresh signals and send telegram if new important signals appear"""
    logger.info("Refreshing cache")
    symbols = ["XAUUSD", "EURUSD", "BTC/USD", "AAPL"]  # CHANGE to your universe
    signals = generate_signals_for_symbols(symbols)
    # compare with previous to send alerts for new buy/sell
    prev = {s["symbol"]: s for s in _cache.get("signals", [])}
    for s in signals:
        prev_s = prev.get(s.symbol)
        if prev_s and prev_s["signal"] != s.signal and s.signal in ("BUY", "SELL"):
            # Send Telegram alert
            text = f"*Signal:* {s.signal}\n*Symbol:* {s.symbol}\n*Strength:* {s.strength}\n*Source:* {s.source}"
            send_telegram(text)
    _cache["signals"] = [sig.dict() for sig in signals]
    _cache["ts"] = int(time.time())
    logger.info("Cache refreshed")


@app.on_event("startup")
def startup_event():
    logger.info("Starting up backend")
    # initial cache fill
    _refresh_cache()
