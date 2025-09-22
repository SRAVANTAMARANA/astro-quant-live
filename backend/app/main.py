# backend/app/main.py
# FastAPI server providing candle fetch + ICT signal endpoints + AI mentor
# Quick-start: pip install fastapi uvicorn requests python-multipart
# Run: uvicorn main:app --host 0.0.0.0 --port 8000 --reload

import os
import time
import math
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Any
from fastapi import FastAPI, Query
from pydantic import BaseModel

app = FastAPI(title="ICT Charting Backend (prototype)")

# =======================
# ==== API KEYS ========
# =======================
# For quick local testing paste your working keys here.
# Later move to os.environ or Docker secrets.
KEYS = {
    "TWELVEDATA": "55a08a202ca740589278abe23d94436a",  # example - replace with your working key
    "ALPHAVANTAGE": "II1CFA2DEF29VF2P",                 # replace
    "FINNHUB": "d38ogk1r01qthpo0oqa0d38ogk1r01qthpo0oqag", # replace or leave blank
}

# =======================
# ==== Utilities ========
# =======================
def ts_to_iso(ts_str):
    try:
        return datetime.fromtimestamp(int(ts_str)).isoformat()
    except:
        return ts_str

def now_utc_iso():
    return datetime.utcnow().isoformat()

# =======================
# ==== Candle fetcher ===
# =======================
def fetch_candles_twelvedata(symbol: str, interval: str = "1min", outputsize: int = 100):
    key = KEYS.get("TWELVEDATA")
    if not key:
        return {"error": "No TwelveData key"}
    url = "https://api.twelvedata.com/time_series"
    params = {"symbol": symbol, "interval": interval, "outputsize": outputsize, "apikey": key, "format":"JSON"}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return {"error": f"td status {r.status_code}"}
    data = r.json()
    if "values" not in data:
        return {"error": "no values", "raw": data}
    # convert to list ascending
    vals = list(reversed(data["values"]))
    # normalize
    entries = []
    for v in vals:
        entries.append({
            "time": v.get("datetime"),
            "open": float(v["open"]),
            "high": float(v["high"]),
            "low": float(v["low"]),
            "close": float(v["close"]),
            "volume": float(v.get("volume", 0))
        })
    return entries

def fetch_candles_alpha(symbol: str, interval: str = "1min", outputsize: int = 100):
    # AlphaVantage has daily/time series; for quick prototyping use intraday
    key = KEYS.get("ALPHAVANTAGE")
    if not key:
        return {"error": "No Alpha key"}
    # try function=TIME_SERIES_INTRADAY
    url = "https://www.alphavantage.co/query"
    params = {"function":"TIME_SERIES_INTRADAY", "symbol":symbol, "interval":interval, "outputsize":"compact", "apikey":key}
    r = requests.get(url, params=params, timeout=15)
    if r.status_code != 200:
        return {"error": f"alpha {r.status_code}"}
    resp = r.json()
    # find key with "Time Series"
    k = next((kk for kk in resp.keys() if "Time Series" in kk), None)
    if not k:
        return {"error": "alpha no timeseries", "raw": resp}
    series = resp[k]
    # series keys descending; we want ascending
    entries = []
    for t in sorted(series.keys()):
        v = series[t]
        entries.append({
            "time": t,
            "open": float(v["1. open"]),
            "high": float(v["2. high"]),
            "low": float(v["3. low"]),
            "close": float(v["4. close"]),
            "volume": float(v.get("5. volume", 0))
        })
    return entries

def get_candles(symbol: str, source="twelvedata", interval="1min", outputsize=200):
    # symbol examples: BTC/USD or EUR/USD or XAU/USD etc.
    # Try prioritized sources
    if source == "twelvedata":
        res = fetch_candles_twelvedata(symbol, interval, outputsize)
        if isinstance(res, list):
            return res
        # fallback alpha
        res2 = fetch_candles_alpha(symbol.replace("/",""), interval, outputsize)
        if isinstance(res2, list):
            return res2
        return {"error": "no data", "td": res, "alpha": res2}
    elif source == "alpha":
        res = fetch_candles_alpha(symbol.replace("/",""), interval, outputsize)
        if isinstance(res, list):
            return res
        return {"error": res}
    else:
        # default try twelvedata
        return get_candles(symbol, "twelvedata", interval, outputsize)

# =======================
# ==== ICT Models  ======
# Simplified prototypes:
#  - order_blocks: local swing highs/lows where strong candle forms and pullback to that area occurs
#  - fvg (Fair Value Gap): bearish/bullish 3-candle gap fill
#  - turtle_soup: false breakout w/ return
#  - liq_sweep: wicks clearing recent swing high/low
# =======================
def detect_order_blocks(candles: List[Dict[str,Any]], lookback=30):
    signals = []
    # find local swing highs/lows by checking candle extremes
    for i in range(2, min(len(candles), lookback)):
        prev = candles[-i-1]
        cur = candles[-i]
        nxt = candles[-i+1] if i>1 else None
        # strong bullish candle then pullback to its body = potential demand OB
        size = cur["close"] - cur["open"]
        if size > 0 and abs(size) / cur["open"] > 0.0025 and nxt:
            # if price pulled back near cur.open
            if abs(nxt["low"] - cur["open"]) / cur["open"] < 0.0035:
                signals.append({
                    "type": "order_block_buy",
                    "index_from_end": i,
                    "price": cur["open"],
                    "time": cur["time"],
                    "note": "Bullish order block (demand) detected"
                })
        # bearish
        size2 = cur["open"] - cur["close"]
        if size2 > 0 and abs(size2) / cur["open"] > 0.0025 and nxt:
            if abs(nxt["high"] - cur["open"]) / cur["open"] < 0.0035:
                signals.append({
                    "type": "order_block_sell",
                    "index_from_end": i,
                    "price": cur["open"],
                    "time": cur["time"],
                    "note": "Bearish order block (supply) detected"
                })
    return signals

def detect_fvg(candles: List[Dict[str,Any]], lookback=60):
    # Fair value gap: three candlestick (A, B, C) where B large and there's a gap between A.high and C.low (classic)
    signals=[]
    n = len(candles)
    for i in range(n-3, n):
        if i < 0: continue
        A = candles[i]
        B = candles[i+1] if i+1 < n else None
        C = candles[i+2] if i+2 < n else None
        if not (B and C): continue
        # bullish FVG condition: A.high < C.low (gap zone)
        if A["high"] < C["low"]:
            signals.append({"type":"fvg_bull", "time":C["time"], "gap_top":C["low"], "gap_bottom":A["high"], "note":"Bullish FVG (gap up) - possible buy on fill"})
        if A["low"] > C["high"]:
            signals.append({"type":"fvg_bear", "time":C["time"], "gap_top":A["low"], "gap_bottom":C["high"], "note":"Bearish FVG (gap down) - possible sell on fill"})
    return signals

def detect_turtle_soup(candles: List[Dict[str,Any]], lookback=50):
    # Simple false-breakout pattern: price briefly exceeds recent high/low but returns inside
    signals=[]
    n=len(candles)
    if n < 6: return signals
    recent_high = max(c["high"] for c in candles[-10:])
    recent_low = min(c["low"] for c in candles[-10:])
    last = candles[-1]
    prev = candles[-2]
    # breakout above recent_high then close back below recent_high
    if prev["high"] > recent_high and last["close"] < recent_high:
        signals.append({"type":"turtle_short_fail","time":last["time"], "price":last["close"], "note":"Failed breakout above high - contrarian short signal"})
    if prev["low"] < recent_low and last["close"] > recent_low:
        signals.append({"type":"turtle_long_fail","time":last["time"], "price":last["close"], "note":"Failed breakdown below low - contrarian long signal"})
    return signals

def detect_liq_sweep(candles: List[Dict[str,Any]], lookback=30):
    # wick that clears a cluster of highs / lows
    signals=[]
    n=len(candles)
    if n < 6: return signals
    highs = [c["high"] for c in candles[-10:]]
    lows = [c["low"] for c in candles[-10:]]
    recent_high = max(highs)
    recent_low = min(lows)
    last = candles[-1]
    if last["high"] > recent_high and last["close"] < recent_high:
        signals.append({"type":"liquidity_sweep_high","time":last["time"], "sweep_price": last["high"], "note":"Liquidity sweep above recent high (sell liquidity) detected"})
    if last["low"] < recent_low and last["close"] > recent_low:
        signals.append({"type":"liquidity_sweep_low","time":last["time"], "sweep_price": last["low"], "note":"Liquidity sweep below recent low (buy liquidity) detected"})
    return signals

# Integrate all detectors
def detect_all(candles):
    res = []
    res.extend(detect_order_blocks(candles))
    res.extend(detect_fvg(candles))
    res.extend(detect_turtle_soup(candles))
    res.extend(detect_liq_sweep(candles))
    # sort by time if possible
    try:
        res_sorted = sorted(res, key=lambda x: x.get("time",""))
    except:
        res_sorted = res
    return res_sorted

# =======================
# ==== API Models =======
# =======================
class CandlesQuery(BaseModel):
    symbol: str
    source: str = "twelvedata"
    interval: str = "1min"
    outputsize: int = 200

# =======================
# ==== Routes ===========
# =======================
@app.get("/health")
def health():
    return {"status":"ok", "time": now_utc_iso()}

@app.get("/candles")
def api_candles(symbol: str = Query(...), source: str = "twelvedata", interval: str = "1min", outputsize: int = 200):
    """
    Fetch candles for symbol. Returns list of candle objects ascending (oldest->newest).
    """
    try:
        c = get_candles(symbol, source, interval, outputsize)
        return {"status":"ok", "symbol":symbol, "source":source, "interval":interval, "count": len(c) if isinstance(c,list) else 0, "data": c}
    except Exception as e:
        return {"status":"error", "error": str(e)}

@app.get("/ict/signals")
def api_ict_signals(symbol: str = Query(...), source: str = "twelvedata", interval: str = "1min", outputsize: int = 300):
    """
    Get combined ICT signals for the provided symbol.
    """
    candles = get_candles(symbol, source, interval, outputsize)
    if isinstance(candles, dict) and candles.get("error"):
        return {"status":"error", "error":candles}
    signals = detect_all(candles)
    return {"status":"ok", "symbol":symbol, "count_candles": len(candles), "signals": signals, "last_candle": candles[-1] if candles else None}

@app.get("/mentor")
def api_mentor(symbol: str = Query(...), source: str = "twelvedata", interval: str = "1min"):
    """
    Simple AI mentor summary: summarise latest signals and provide narrative lines.
    """
    sc = get_candles(symbol, source, interval, 300)
    if isinstance(sc, dict) and sc.get("error"):
        return {"status":"error", "error": sc}
    signals = detect_all(sc)
    narrative_lines = []
    now = now_utc_iso()
    narrative_lines.append(f"Mentor report for {symbol} at {now}.")
    if not signals:
        narrative_lines.append("No immediate ICT setups detected in the recent bars. Stay flat and monitor for liquidity sweeps or order block retests.")
    else:
        narrative_lines.append(f"{len(signals)} setup(s) detected:")
        for s in signals:
            t = s.get("time", "")
            note = s.get("note","")
            price = s.get("price") or s.get("sweep_price") or s.get("gap_top") or ""
            narrative_lines.append(f"- {s['type']} at {price} time {t}. {note}")
    # suggested actions (very basic)
    narrative_lines.append("Suggested approach: wait for retest of the setup area, confirm with volume and a rejection candle, then enter with tight stoploss. Use risk management.")
    return {"status":"ok", "symbol":symbol, "signals":signals, "narrative": narrative_lines}

# =======================
# ==== Root ============
# =======================
@app.get("/")
def root():
    return {"message":"ICT Backend up", "time": now_utc_iso()}
