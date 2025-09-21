#!/usr/bin/env python3
"""
fetch_and_send_twelvedata.py

Usage:
  python /app/fetch_and_send_twelvedata.py "XAU/USD" "5min"

Reads TWELVEDATA_API_KEY from environment, fetches candles from TwelveData,
and POSTs them to the local ICT endpoint /ict/fvg.
"""

import os
import sys
import time
import requests

TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
ICT_BASE = os.getenv("ICT_BASE_URL", "http://localhost:8000")  # container-local
ICT_ENDPOINT = f"{ICT_BASE}/ict/fvg"

if not TWELVEDATA_KEY:
    print("ERROR: TWELVEDATA_API_KEY not set in environment")
    sys.exit(2)

def fetch_candles(symbol: str, interval: str = "5min", outputsize: int = 100):
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
        "apikey": TWELVEDATA_KEY,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def normalize_twelvedata_json(j):
    # TwelveData returns "values": [{...}, ...] with keys: datetime, open, high, low, close, volume
    values = j.get("values") or []
    # convert each to numeric floats and unix time if needed
    normalized = []
    for v in reversed(values):  # reverse if you want oldest->newest
        try:
            cand = {
                "time": v.get("datetime"),  # ISO string; if you need epoch convert later
                "open": float(v.get("open", 0)),
                "high": float(v.get("high", 0)),
                "low": float(v.get("low", 0)),
                "close": float(v.get("close", 0)),
                "volume": float(v.get("volume", 0)) if v.get("volume") is not None else None,
            }
        except Exception:
            # fallback: keep raw
            cand = v
        normalized.append(cand)
    return normalized

def post_to_ict(symbol: str, interval: str, candles):
    payload = {
        "symbol": symbol,
        "interval": interval,
        "candles": candles,
    }
    headers = {"Content-Type": "application/json"}
    r = requests.post(ICT_ENDPOINT, json=payload, headers=headers, timeout=20)
    return r

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python fetch_and_send_twelvedata.py <SYMBOL> <INTERVAL> (eg. \"XAU/USD\" 5min)")
        sys.exit(1)

    symbol = sys.argv[1]
    interval = sys.argv[2]

    try:
        print("Fetching from TwelveData:", symbol, interval)
        j = fetch_candles(symbol, interval, outputsize=100)
        if "values" not in j:
            print("TwelveData returned:", j)
            sys.exit(3)
        candles = normalize_twelvedata_json(j)
        print(f"Fetched {len(candles)} candles. Posting to {ICT_ENDPOINT} ...")
        r = post_to_ict(symbol, interval, candles)
        print("ICT response:", r.status_code, r.text)
        if r.status_code >= 400:
            sys.exit(4)
    except requests.RequestException as e:
        print("Network / API error:", str(e))
        sys.exit(5)
    except Exception as e:
        print("Unhandled error:", str(e))
        sys.exit(6)
