# backend/app/ict_twelvedata.py
import os
from typing import List, Dict, Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
import httpx
import asyncio

router = APIRouter()

TWELVEDATA_API_KEY = os.getenv("TWELVEDATA_API_KEY")  # make sure .env contains this

class FetchRequest(BaseModel):
    symbol: str = Field(..., example="XAUUSD")
    interval: str = Field(..., example="5min")
    limit: int = Field(100, example=100)  # how many candles to fetch (max ~5000 maybe)


async def fetch_twelvedata_time_series(
    symbol: str, interval: str, limit: int, apikey: str
) -> Dict[str, Any]:
    """Fetch time series from TwelveData asynchronously with httpx."""
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": str(limit),
        "format": "JSON",
        "apikey": apikey,
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        r = await client.get(url, params=params)
        # raise_for_status will throw for 4xx/5xx
        try:
            r.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise HTTPException(status_code=502, detail=f"TwelveData error: {exc.response.text}")

        return r.json()


def convert_twelvedata_values_to_candles(values: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """TwelveData returns values in reverse chronological order; convert to chrono and map fields."""
    # values is a list of dictionaries like { "datetime": "...", "open": "...", "high": "...", ... }
    # Convert strings to floats where appropriate and ensure chronological order
    candles = []
    for v in reversed(values):  # reverse to chronological (oldest -> newest)
        try:
            candle = {
                "time": v.get("datetime") or v.get("timestamp"),
                "open": float(v["open"]),
                "high": float(v["high"]),
                "low": float(v["low"]),
                "close": float(v["close"]),
                "volume": float(v.get("volume", 0) or 0),
            }
        except Exception:
            # skip malformed candle
            continue
        candles.append(candle)
    return candles


@router.post("/ict/fvg_auto")
async def ict_fvg_auto(req: FetchRequest):
    """Fetch candles from TwelveData and return candles + placeholder signals.

    Sample payload:
    {
      "symbol": "XAUUSD",
      "interval": "5min",
      "limit": 100
    }

    Make sure TWELVEDATA_API_KEY is set in .env (and loaded into container).
    """
    if not TWELVEDATA_API_KEY:
        raise HTTPException(status_code=500, detail="TWELVEDATA_API_KEY not set in env")

    # fetch
    data = await fetch_twelvedata_time_series(req.symbol, req.interval, req.limit, TWELVEDATA_API_KEY)

    # check for API error in payload
    if "status" in data and data.get("status") == "error":
        msg = data.get("message", "unknown error from TwelveData")
        raise HTTPException(status_code=502, detail=f"TwelveData error: {msg}")

    values = data.get("values")
    if not values:
        raise HTTPException(status_code=502, detail="TwelveData returned no candle values")

    candles = convert_twelvedata_values_to_candles(values)

    # TODO: Replace this placeholder with your real ICT signal detection routine.
    # For now, return an empty signals array and the candles for inspection/testing.
    signals = []  # <-- integrate your ICT logic here

    return {"status": "ok", "symbol": req.symbol, "interval": req.interval, "candles_count": len(candles), "candles": candles, "signals": signals}
