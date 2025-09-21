#!/usr/bin/env python3
"""
Fetch candles from TwelveData and send them into AstroQuant ICT backend.
"""

import os
import requests
from datetime import datetime, timedelta

BACKEND_URL = "http://localhost:8000/ict/fvg"

def epoch_ms(ts):
    return int(ts * 1000)

def fetch_twelvedata(symbol="XAU/USD", interval="5min", minutes=240):
    key = os.environ.get("TWELVEDATA_API_KEY")
    if not key:
        raise RuntimeError("TWELVEDATA_API_KEY not set in environment")

    end = datetime.utcnow()
    start = end - timedelta(minutes=minutes)

    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 5000,
        "start_date": start.isoformat(),
        "end_date": end.isoformat(),
        "apikey": key
    }

    r = requests.get(url, params=params, timeout=20)
    r.raise_for_status()
    data = r.json()

    if "values" not in data:
        raise RuntimeError(f"TwelveData error: {data}")

    # Reverse to chronological order
    values = list(reversed(data["values"]))
    candles = []
    for v in values:
        dt = datetime.fromisoformat(v["datetime"])
        candles.append({
            "time": epoch_ms(dt.timestamp()),
            "open": float(v["open"]),
            "high": float(v["high"]),
            "low": float(v["low"]),
            "close": float(v["close"]),
            "volume": float(v.get("volume", 0)),
        })
    return candles

def send_to_backend(symbol, candles):
    payload = {"symbol": symbol, "candles": candles}
    r = requests.post(BACKEND_URL, json=payload, timeout=30)
    r.raise_for_status()
    return r.json()

if __name__ == "__main__":
    symbol = "XAU/USD"
    interval = "5min"
    candles = fetch_twelvedata(symbol, interval, minutes=240)
    print(f"Fetched {len(candles)} candles from TwelveData.")
    resp = send_to_backend(symbol, candles)
    print("Backend response:", resp)
