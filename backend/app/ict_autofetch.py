# backend/app/ict_autofetch.py
import os
import time
import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any

router = APIRouter(prefix="/ict", tags=["ict"])

TWELVE_ENV = "TWELVEDATA_API_KEY"
TWELVE_URL = "https://api.twelvedata.com/time_series"

class AutoFVGRequest(BaseModel):
    symbol: str
    interval: str = "5min"
    limit: int = 100

# ----- IMPORT YOUR REAL FVG FUNCTION HERE -----
# Try these fallbacks; replace with the exact import path if you know it.
try:
    # common pattern: backend/app/ict.py or backend/app/fvg.py
    from app.ict import compute_fvg_from_candles  # preferred if present
except Exception:
    try:
        from app.fvg import compute_fvg_from_candles
    except Exception:
        try:
            # If your project uses a module named "routes" or "services"
            from app.routes.ict import compute_fvg_from_candles
        except Exception:
            # Last fallback: define a dummy function — replace manually!
            def compute_fvg_from_candles(candles: List[Dict[str, Any]]) -> Dict[str, Any]:
                # TODO: replace with your real function.
                # For now returns empty signals for safety.
                return {"fvg_signals": []}

# ----- TwelveData fetch helper -----
def fetch_twelvedata_candles(symbol: str, interval: str, outputsize: int, api_key: str) -> List[Dict[str, Any]]:
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
        "apikey": api_key
    }
    r = requests.get(TWELVE_URL, params=params, timeout=15)
    if r.status_code != 200:
        raise HTTPException(status_code=502, detail=f"TwelveData HTTP {r.status_code}")
    data = r.json()
    # The time series list is typically in data['values']
    if "status" in data and data.get("status") == "error":
        raise HTTPException(status_code=502, detail=f"TwelveData error: {data.get('message')}")
    values = data.get("values") or data.get("values", [])
    if not values:
        # Sometimes TwelveData returns 'values' or 'values' key; guard
        raise HTTPException(status_code=502, detail="No 'values' returned by TwelveData")
    candles = []
    # TwelveData usually returns newest-first, reverse -> oldest-first
    for v in reversed(values):
        # v expected to have 'datetime', 'open', 'high', 'low', 'close'
        dt_str = v.get("datetime") or v.get("datetime")
        # Accept either full time string or ISO etc.
        # Try several parse patterns
        try:
            # expect format "YYYY-MM-DD HH:MM:SS"
            t_struct = time.strptime(dt_str, "%Y-%m-%d %H:%M:%S")
            epoch = int(time.mktime(t_struct))
        except Exception:
            # fallback: if we already have epoch numeric string
            try:
                epoch = int(float(v.get("timestamp") or v.get("time", 0)))
            except Exception:
                epoch = int(time.time())
        candle = {
            "time": epoch,
            "open": float(v["open"]),
            "high": float(v["high"]),
            "low": float(v["low"]),
            "close": float(v["close"]),
        }
        candles.append(candle)
    return candles

# ----- endpoint -----
@router.post("/fvg_auto")
def fvg_auto(req: AutoFVGRequest):
    api_key = os.getenv(TWELVE_ENV)
    if not api_key:
        raise HTTPException(status_code=500, detail=f"Missing env var {TWELVE_ENV}")
    candles = fetch_twelvedata_candles(req.symbol, req.interval, req.limit, api_key)
    # call your real FVG function which should accept a list of candles
    result = compute_fvg_from_candles(candles)
    return {"status": "ok", "symbol": req.symbol, "candles_count": len(candles), **(result or {})}
