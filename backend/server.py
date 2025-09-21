# server.py
# Single-file FastAPI app that fetches candles from Finnhub when not provided and runs a placeholder FVG processing.
# Requirements: fastapi, uvicorn, httpx, python-dotenv (optional to load .env in development)
#
# Install dependencies (if running locally):
# pip install fastapi uvicorn httpx python-dotenv

import os
import time
from typing import List, Optional, Any, Dict
import httpx
from fastapi import FastAPI, HTTPException, Request
from pydantic import BaseModel

# Optionally load local .env when running locally (not needed when running via docker-compose with env_file)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

app = FastAPI(title="AstroQuant Backend - ICT helper", version="0.1")

# Map common interval strings -> Finnhub resolution
_RES_MAP = {
    "1m": "1", "5m": "5", "15m": "15", "30m": "30", "60m": "60",
    "1h": "60", "4h": "60", "1d": "D", "D": "D"
}

class Candle(BaseModel):
    time: int
    open: float
    high: float
    low: float
    close: float

class FVGRequest(BaseModel):
    symbol: Optional[str] = None
    interval: Optional[str] = "5m"
    limit: Optional[int] = 200
    candles: Optional[List[Candle]] = None
    # allow extra fields
    class Config:
        extra = "allow"

@app.get("/health")
async def health():
    return {"status": "ok"}

async def fetch_candles_finnhub(symbol: str, interval: str, limit: int = 200) -> List[Dict[str, Any]]:
    """
    Fetch OHLC candles from Finnhub.io
    Returns list of dicts: {"time": ts, "open": o, "high": h, "low": l, "close": c}
    """
    key = os.getenv("FINNHUB_API_KEY", "").strip()
    if not key:
        raise RuntimeError("FINNHUB_API_KEY not set in environment")

    resolution = _RES_MAP.get(interval)
    if resolution is None:
        # If e.g. "5m" not in map, try exact numeric fallback
        if interval.endswith("m") and interval[:-1].isdigit():
            resolution = interval[:-1]
        else:
            raise ValueError(f"Unsupported interval '{interval}'")

    now = int(time.time())
    if resolution == "D":
        sec_per_candle = 24 * 3600
    else:
        sec_per_candle = int(resolution) * 60

    from_ts = max(0, now - limit * sec_per_candle)
    to_ts = now

    url = (
        f"https://finnhub.io/api/v1/stock/candle"
        f"?symbol={symbol}&resolution={resolution}&from={from_ts}&to={to_ts}&token={key}"
    )
    async with httpx.AsyncClient(timeout=20.0) as client:
        r = await client.get(url)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"Finnhub error: {r.status_code} {r.text}")

    data = r.json()
    if data.get("s") != "ok":
        raise HTTPException(status_code=404, detail=f"Finnhub returned status: {data.get('s')}")

    times = data.get("t", [])
    opens = data.get("o", [])
    highs = data.get("h", [])
    lows = data.get("l", [])
    closes = data.get("c", [])

    n = min(len(times), len(opens), len(highs), len(lows), len(closes))
    candles = []
    for i in range(n):
        candles.append({
            "time": int(times[i]),
            "open": float(opens[i]),
            "high": float(highs[i]),
            "low": float(lows[i]),
            "close": float(closes[i])
        })
    return candles

def process_fvg_placeholder(candles: List[Dict[str, Any]], symbol: Optional[str] = None) -> Dict[str, Any]:
    """
    Placeholder for your FVG processing logic. Replace this with real logic.
    - receives a list of candles (dicts with time/open/high/low/close)
    - returns sample analysis result
    """
    # simple illustrative values:
    n = len(candles)
    latest = candles[-1] if n > 0 else {}
    return {
        "status": "processed",
        "symbol": symbol,
        "candles_received": n,
        "latest_close": latest.get("close"),
        "message": "Replace process_fvg_placeholder with your real FVG analyzer"
    }

@app.post("/ict/fvg")
async def ict_fvg(req: Request):
    """
    Accepts JSON payload:
      - either supply "candles": [ {time,open,high,low,close}, ... ]
      - OR supply "symbol" and optional "interval" (default 5m) and backend will fetch candles from Finnhub
    """
    payload = await req.json()
    # Try to parse Pydantic model (allow extra)
    # Use incoming candles if present
    candles_payload = payload.get("candles")
    if candles_payload is None:
        # attempt fetch using symbol + interval
        symbol = payload.get("symbol")
        interval = payload.get("interval", "5m")
        limit = int(payload.get("limit", 200))
        if not symbol:
            raise HTTPException(status_code=400, detail="Either 'candles' or 'symbol' must be provided")
        try:
            candles = await fetch_candles_finnhub(symbol, interval, limit=limit)
        except HTTPException as he:
            raise he
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Failed fetching candles: {str(e)}")
    else:
        # validate minimal structure
        if not isinstance(candles_payload, list) or len(candles_payload) == 0:
            raise HTTPException(status_code=400, detail="candles must be a non-empty list")
        # ensure numeric types
        candles = []
        for c in candles_payload:
            try:
                candles.append({
                    "time": int(c["time"]),
                    "open": float(c["open"]),
                    "high": float(c["high"]),
                    "low": float(c["low"]),
                    "close": float(c["close"])
                })
            except Exception as e:
                raise HTTPException(status_code=400, detail=f"Invalid candle format: {e}")

        symbol = payload.get("symbol")

    # Call your FVG processing code here. Right now uses a placeholder.
    result = process_fvg_placeholder(candles, symbol=symbol)
    return result

# Optional root info
@app.get("/")
def root():
    return {"info": "AstroQuant backend running. Use /health and /ict/fvg"}

# Run: uvicorn server:app --host 0.0.0.0 --port 8000
