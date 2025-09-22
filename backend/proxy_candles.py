# backend/proxy_candles.py
from fastapi import APIRouter, Query, HTTPException
import requests
from typing import Optional

router = APIRouter()

# ---- PROVIDER KEYS (you said skip env, so they are embedded here) ----
TWELVEDATA_KEY = "55a08a202ca740589278abe23d94436a"      # replace with your key string
ALPHAV_KEY     = "YOUR_ALPHAV_KEY"          # replace with your key string
FINNHUB_KEY    = "d38ogk1r01qthpo0oqa0d38ogk1r01qthpo0oqag"         # replace with your key string
# ---------------------------------------------------------------------

def twelvedata_request(symbol: str, interval: str, limit: int):
    # twelvedata expects symbol format like: XAU/USD or BTC/USD or EUR/USD
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": limit,
        "format": "JSON",
        "apikey": TWELVEDATA_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"TwelveData bad status {r.status_code}")
    data = r.json()
    # Normalize TwelveData -> standard candle list
    if "values" in data:
        values = data["values"]
        # TwelveData returns newest-first; convert to oldest-first if needed
        values = list(reversed(values))
        candles = []
        for v in values:
            candles.append({
                "datetime": v.get("datetime"),
                "open": float(v.get("open")),
                "high": float(v.get("high")),
                "low": float(v.get("low")),
                "close": float(v.get("close")),
                "volume": float(v.get("volume", 0))
            })
        return {"provider": "twelvedata", "candles": candles}
    raise RuntimeError("TwelveData: no values")

def alphav_request(symbol: str, interval: str, limit: int):
    # AlphaVantage: their forex/time series endpoints are different.
    # For simplicity, try TIME_SERIES_INTRADAY for equities or FX endpoints depending on symbol.
    # We attempt TIME_SERIES_INTRADAY if symbol looks like "SYMBOL" else FX intraday for pairs.
    # For real production, you must implement exact AV mappings.
    url = "https://www.alphavantage.co/query"
    # alpha uses INTERVAL like "1min", "5min" - ensure proper param
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol.replace("/", ""),
        "interval": interval,
        "outputsize": "compact",
        "apikey": ALPHAV_KEY
    }
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"AlphaVantage bad status {r.status_code}")
    data = r.json()
    # try to find time series keys
    ts_key = None
    for k in data.keys():
        if "Time Series" in k:
            ts_key = k
            break
    if not ts_key:
        raise RuntimeError("AlphaVantage: no timeseries")
    items = data[ts_key]
    # items is dict datetime->ohlc, sorted newest-first
    items_list = sorted(items.items(), key=lambda x: x[0])
    candles = []
    for dt, v in items_list[:limit]:
        candles.append({
            "datetime": dt,
            "open": float(v.get("1. open")),
            "high": float(v.get("2. high")),
            "low": float(v.get("3. low")),
            "close": float(v.get("4. close")),
            "volume": float(v.get(list(v.keys())[-1], 0))
        })
    return {"provider": "alphavantage", "candles": candles}

def finnhub_request(symbol: str, interval: str, limit: int):
    # Finnhub: use /api/v1/forex/candle or /crypto/candle depending on symbol
    # Map interval strings to Finnhub resolution:
    res_map = {
        "1min": "1",
        "5min": "5",
        "15min": "15",
        "30min": "30",
        "60min": "60"
    }
    resolution = res_map.get(interval, "1")
    # compute epoch times
    import time
    to_ts = int(time.time())
    from_ts = to_ts - (limit * 60)  # naive: limit minutes back for 1min; not exact for 5min but ok
    # choose endpoint: if symbol contains '/', treat as FX (e.g. OANDA: "OANDA:EUR_USD" not standard). For simplicity try crypto first then forex.
    url = f"https://finnhub.io/api/v1/forex/candle"
    params = {"symbol": symbol, "resolution": resolution, "from": from_ts, "to": to_ts, "token": FINNHUB_KEY}
    r = requests.get(url, params=params, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"Finnhub bad status {r.status_code}")
    data = r.json()
    if data.get("s") != "ok":
        raise RuntimeError("Finnhub no data")
    # Finnhub returns arrays
    candles = []
    for i, t in enumerate(data["t"][:limit]):
        candles.append({
            "datetime": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime(t)),
            "open": float(data["o"][i]),
            "high": float(data["h"][i]),
            "low": float(data["l"][i]),
            "close": float(data["c"][i]),
            "volume": float(data.get("v", [0]*len(data["t"]))[i])
        })
    return {"provider": "finnhub", "candles": candles}

@router.get("/ict/candles")
def get_candles(symbol: str = Query(..., description="Symbol e.g. XAU/USD or BTC/USD or EUR/USD"),
                interval: str = Query("1min", description="Interval e.g. 1min, 5min"),
                limit: int = Query(50, description="Number of bars to return")):
    # Try each provider in order; return first success
    # Normalize symbol for providers:
    sym = symbol
    # Common normalization: if user passed XAUUSD -> convert to XAU/USD for twelvedata
    if "/" not in sym and len(sym) >= 6:
        # naive split for pairs like EURUSD -> EUR/USD
        if len(sym) % 3 == 0:
            sym = sym[:3] + "/" + sym[3:]
    providers = [
        ("twelvedata", lambda: twelvedata_request(sym, interval, limit)),
        ("alphavantage", lambda: alphav_request(sym.replace("/", ""), interval, limit)),
        ("finnhub", lambda: finnhub_request(sym.replace("/", ""), interval, limit)),
    ]
    errors = {}
    for name, fn in providers:
        try:
            res = fn()
            return res
        except Exception as e:
            errors[name] = str(e)
            continue
    # if none worked:
    raise HTTPException(status_code=502, detail={"msg": "No provider returned data", "errors": errors})
