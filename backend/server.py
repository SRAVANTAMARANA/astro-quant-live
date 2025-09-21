# backend/server.py
# FastAPI backend - unified "signals" endpoint combining multiple APIs
# Async, uses httpx
import os
from dotenv import load_dotenv
# Load environment variables from .env
load_dotenv()
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

import httpx
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# optional simple in-memory cache
_CACHE: Dict[str, Dict[str, Any]] = {}

app = FastAPI(title="AstroQuant Backend (API aggregator)")

# allow frontend origin (adjust origin(s) in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # for local dev; tighten for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# read keys from environment (set in .env and docker-compose)
TWELVE_KEY = os.getenv("TWELVEDATA_API_KEY", "")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
ALPHAV_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# Utilities: caching helper
def cache_get(key: str, max_age_seconds=20):
    rec = _CACHE.get(key)
    if not rec:
        return None
    if (datetime.utcnow() - rec["ts"]).total_seconds() > max_age_seconds:
        return None
    return rec["value"]

def cache_set(key: str, value: Any):
    _CACHE[key] = {"value": value, "ts": datetime.utcnow()}


# Pydantic response model (simple)
class SignalResp(BaseModel):
    symbol: str
    price: Optional[float] = None
    source_prices: Dict[str, Any] = {}
    news: List[Dict[str, Any]] = []
    meta: Dict[str, Any] = {}


# Async fetch helpers using httpx
async def fetch_twelvedata_quote(symbol: str) -> Dict[str, Any]:
    # TwelveData example: https://twelvedata.com/docs
    if not TWELVE_KEY:
        return {"error": "no_twelvedata_key"}
    url = "https://api.twelvedata.com/price"
    params = {"symbol": symbol, "apikey": TWELVE_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        if resp.status_code != 200:
            return {"error": f"td_status:{resp.status_code}", "text": resp.text[:200]}
        data = resp.json()
        return data


async def fetch_finnhub_quote_and_news(symbol: str) -> Dict[str, Any]:
    # Finnhub quote & company news
    if not FINNHUB_KEY:
        return {"error": "no_finnhub_key"}
    base = "https://finnhub.io/api/v1"
    async with httpx.AsyncClient(timeout=10.0) as client:
        qurl = f"{base}/quote"
        params = {"symbol": symbol, "token": FINNHUB_KEY}
        qresp = await client.get(qurl, params=params)
        # news (past 7 days)
        today = datetime.utcnow().date()
        frm = (today - timedelta(days=7)).isoformat()
        to = today.isoformat()
        nurl = f"{base}/company-news"
        nresp = await client.get(nurl, params={"symbol": symbol, "from": frm, "to": to, "token": FINNHUB_KEY})
        out = {
            "quote": qresp.json() if qresp.status_code == 200 else {"error": qresp.text},
            "news": nresp.json() if nresp.status_code == 200 else {"error": nresp.text},
        }
        return out


async def fetch_alpha_vantage_quote(symbol: str) -> Dict[str, Any]:
    if not ALPHAV_KEY:
        return {"error": "no_alpha_v_key"}
    url = "https://www.alphavantage.co/query"
    params = {"function": "GLOBAL_QUOTE", "symbol": symbol, "apikey": ALPHAV_KEY}
    async with httpx.AsyncClient(timeout=10.0) as client:
        resp = await client.get(url, params=params)
        return resp.json()


async def get_combined_symbol_data(symbol: str) -> SignalResp:
    # caching by symbol
    cache_key = f"symbol:{symbol}"
    cached = cache_get(cache_key, max_age_seconds=20)
    if cached:
        return cached

    # run API calls concurrently
    results = await asyncio.gather(
        fetch_twelvedata_quote(symbol),
        fetch_finnhub_quote_and_news(symbol),
        fetch_alpha_vantage_quote(symbol),
    )

    td, fh, av = results

    # build a combined result
    out = SignalResp(
        symbol=symbol,
        price=None,
        source_prices={
            "twelvedata": td,
            "finnhub": fh.get("quote") if isinstance(fh, dict) else fh,
            "alphavantage": av,
        },
        news=(fh.get("news") if isinstance(fh, dict) else []) or [],
        meta={
            "fetched_at": datetime.utcnow().isoformat(),
        },
    )

    # try to set primary price from sources in order
    try:
        # twelvedata returns {"price": "1234.56"}
        if isinstance(td, dict) and "price" in td:
            out.price = float(td["price"])
        elif isinstance(fh, dict) and "quote" in fh and isinstance(fh["quote"], dict) and "c" in fh["quote"]:
            out.price = float(fh["quote"]["c"])
        elif isinstance(av, dict) and "Global Quote" in av and "05. price" in av["Global Quote"]:
            out.price = float(av["Global Quote"]["05. price"])
    except Exception:
        # ignore parsing errors
        pass

    cache_set(cache_key, out)
    return out


async def send_telegram_message(text: str) -> Dict[str, Any]:
    # Basic Telegram notify helper - only if bot token and chat id exist
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"error": "no_telegram_config"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.post(url, json=payload)
        return r.json()


@app.get("/signals", response_model=List[SignalResp])
async def signals(symbols: Optional[str] = "XAUUSD,EURUSD,USDJPY"):
    """
    /signals?symbols=XAUUSD,EURUSD
    Returns a list of symbol data combined from multiple APIs.
    """

    symbol_list = [s.strip().upper() for s in symbols.split(",") if s.strip()]
    tasks = [get_combined_symbol_data(s) for s in symbol_list]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    out = []
    for r in results:
        if isinstance(r, Exception):
            out.append({"symbol": "ERROR", "meta": {"error": str(r)}})
        else:
            out.append(r)

    # Example: if big move or special condition, send Telegram notification
    # Simple rule: if XAUUSD moved > 0.5% (just example)
    try:
        for s in out:
            if isinstance(s, SignalResp) and s.symbol.upper() == "XAUUSD" and s.price:
                # compute relative change using Finnhub quote 'pc' previous close if available
                fh_q = s.source_prices.get("finnhub", {})
                prev_close = None
                if isinstance(fh_q, dict):
                    prev_close = fh_q.get("pc") or fh_q.get("p")  # fallback
                if prev_close:
                    try:
                        prev_close = float(prev_close)
                        curr = float(s.price)
                        pct = abs(curr - prev_close) / prev_close * 100.0
                        if pct > 0.5:
                            await send_telegram_message(f"AstroQuant Alert: {s.symbol} moved {pct:.2f}% now {curr}")
                    except Exception:
                        pass
    except Exception:
        pass

    # convert SignalResp objects to dicts for JSON response
    final = []
    for s in out:
        if isinstance(s, SignalResp):
            final.append(s.dict())
        else:
            final.append(s)
    return final


@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.utcnow().isoformat()}
