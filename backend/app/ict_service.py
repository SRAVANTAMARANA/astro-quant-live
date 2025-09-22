# backend/app/ict_service.py
# Run with e.g. `uvicorn ict_service:app --host 0.0.0.0 --port 8000`
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os, time, requests, statistics, math
from typing import List, Dict, Any, Optional

app = FastAPI(title="ICT Charting API (failover providers)")

# env keys (backend/.env must expose these to container)
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY", "")
FINNHUB_KEY    = os.getenv("FINNHUB_API_KEY", "")
ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "")
TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT  = os.getenv("TELEGRAM_CHAT_ID", "")

# ---------- utilities ----------
def _req_get(url, params=None, headers=None, timeout=8):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        # return exception for caller decision
        return {"_error": str(e)}

def _normalize_candle_list(candles: List[Dict[str,Any]]) -> List[Dict[str,Any]]:
    """
    Expect list of dicts with keys: datetime/open/high/low/close (strings or numbers).
    Convert to numeric and unix timestamp for 't'.
    """
    out = []
    for c in candles:
        try:
            dt = c.get("datetime") or c.get("time") or c.get("t") or c.get("timestamp")
            # If 't' is present as integer -> keep
            tval = None
            if isinstance(dt, (int, float)):
                tval = int(dt)
            else:
                # try ISO string -> time.mktime
                if isinstance(dt, str):
                    # attempt parse naive ISO (remove timezone)
                    try:
                        # Try to parse as YYYY-MM-DD HH:MM:SS or YYYY-MM-DDTHH:MM:SS
                        import datetime as _dt
                        s = dt.replace("T", " ").split("+")[0].split("Z")[0]
                        d = _dt.datetime.strptime(s, "%Y-%m-%d %H:%M:%S")
                        tval = int(d.timestamp())
                    except Exception:
                        # fallback 0
                        tval = 0
                else:
                    tval = 0
            o = float(c.get("open", c.get("o", 0)))
            h = float(c.get("high", c.get("h", 0)))
            l = float(c.get("low", c.get("l", 0)))
            cval = float(c.get("close", c.get("c", c.get("close", 0))))
            out.append({"t": tval, "o": o, "h": h, "l": l, "c": cval})
        except Exception:
            continue
    # sort by t
    out.sort(key=lambda x: x["t"])
    return out

# ---------- Provider fetchers (failover order) ----------
def fetch_twelvedata(symbol: str, interval: str="1min", outputsize: int=100) -> Dict[str,Any]:
    """Return dict {status:..., data: [candles...]} or error dict."""
    if not TWELVEDATA_KEY:
        return {"_error": "no_twelvedata_key"}
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "apikey": TWELVEDATA_KEY,
        "format": "JSON"
    }
    resp = _req_get(url, params=params)
    if resp is None or "_error" in resp:
        return {"_error": resp.get("_error") if resp else "no_response"}
    if resp.get("status") == "ok" and "values" in resp:
        candles = []
        for v in resp["values"]:
            candles.append({
                "datetime": v.get("datetime") or v.get("timestamp"),
                "open": v.get("open"),
                "high": v.get("high"),
                "low": v.get("low"),
                "close": v.get("close")
            })
        return {"status":"ok", "candles": _normalize_candle_list(candles)}
    else:
        # API error text
        return {"_error": resp}

def fetch_finnhub(symbol: str, interval: str="1", outputsize: int=100) -> Dict[str,Any]:
    # finnhub uses resolution param: 1, 5, 15, 60, D
    if not FINNHUB_KEY:
        return {"_error": "no_finnhub_key"}
    # Finnhub expects e.g. symbol='BINANCE:BTCUSDT' or 'BTCUSDT' for crypto with token?
    # We'll try FInnHub quote candle endpoint: /indicator? but simplest: use quote or candles
    url = "https://finnhub.io/api/v1/crypto/candle"
    # default: assume symbol is like "BINANCE:BTCUSDT" for crypto; for stocks, use symbol param below
    params = {
        "symbol": symbol,   # pass BINANCE:BTCUSDT for crypto
        "resolution": interval,
        "from": int(time.time()) - 3600*24,
        "to": int(time.time()),
        "token": FINNHUB_KEY
    }
    resp = _req_get(url, params=params)
    if resp is None or "_error" in resp:
        return {"_error": resp.get("_error") if resp else "no_response"}
    # Finnhub returns c, h, l, o, t arrays
    if resp.get("s") == "ok" and "t" in resp:
        candles = []
        for i, tt in enumerate(resp["t"]):
            candles.append({
                "datetime": int(tt),
                "open": resp["o"][i],
                "high": resp["h"][i],
                "low": resp["l"][i],
                "close": resp["c"][i]
            })
        return {"status":"ok", "candles": _normalize_candle_list(candles)}
    else:
        return {"_error": resp}

def fetch_alpha(symbol: str, interval: str="1min", outputsize: int=100) -> Dict[str,Any]:
    if not ALPHAVANTAGE_KEY:
        return {"_error": "no_alphavantage_key"}
    # Alphavantage endpoints: TIME_SERIES_INTRADAY for stocks; for crypto use DIGITAL_CURRENCY_INTRADAY (limited)
    # We'll call TIME_SERIES_INTRADAY for symbol as provided (works for stocks)
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "TIME_SERIES_INTRADAY",
        "symbol": symbol,
        "interval": interval,
        "apikey": ALPHAVANTAGE_KEY,
        "outputsize": "compact"
    }
    resp = _req_get(url, params=params)
    if resp is None or "_error" in resp:
        return {"_error": resp.get("_error") if resp else "no_response"}
    # Alphavantage returns e.g. "Time Series (1min)" key
    key = None
    for k in resp.keys():
        if "Time Series" in k:
            key = k
            break
    if key:
        candles = []
        for dt, v in resp[key].items():
            candles.append({
                "datetime": dt,
                "open": v["1. open"],
                "high": v["2. high"],
                "low": v["3. low"],
                "close": v["4. close"]
            })
        return {"status":"ok", "candles": _normalize_candle_list(candles)}
    else:
        return {"_error": resp}

# ---------- Failover logic ----------
def fetch_candles_with_failover(symbol: str, interval="1min", outputsize=150):
    # Priority: TwelveData -> Finnhub -> AlphaVantage
    # User can pass crypto exchange format to finnhub e.g. BINANCE:BTCUSDT
    # Normalize symbol for twelvedata input (TwelveData supports many notations)
    # Try TwelveData
    r = fetch_twelvedata(symbol, interval=interval, outputsize=outputsize)
    if r.get("status") == "ok":
        return {"provider":"twelvedata", "candles": r["candles"]}
    # Try Finnhub
    r2 = fetch_finnhub(symbol, interval=interval, outputsize=outputsize)
    if r2.get("status") == "ok":
        return {"provider":"finnhub", "candles": r2["candles"]}
    # Try AlphaVantage
    r3 = fetch_alpha(symbol, interval=interval, outputsize=outputsize)
    if r3.get("status") == "ok":
        return {"provider":"alphavantage", "candles": r3["candles"]}
    # All failed — combine errors
    return {"provider": None, "error": {"twelvedata": r, "finnhub": r2, "alphavantage": r3}}

# ---------- Signal computation (simple ICT-style baseline) ----------
def sma(values: List[float], period: int) -> Optional[float]:
    if len(values) < period:
        return None
    return sum(values[-period:]) / period

def compute_rsi(closes: List[float], period: int=14) -> Optional[float]:
    if len(closes) < period+1:
        return None
    gains = []
    losses = []
    for i in range(-period, 0):
        change = closes[i] - closes[i-1]
        if change > 0:
            gains.append(change)
            losses.append(0)
        else:
            gains.append(0)
            losses.append(abs(change))
    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100 - (100 / (1 + rs))

def compute_ict_signals(candles: List[Dict[str,Any]]) -> Dict[str,Any]:
    """
    Simple signals:
      - SMA fast (9) / slow (21) crossover -> buy/sell
      - RSI(14) threshold (overbought/oversold)
    """
    closes = [c["c"] for c in candles]
    latest = closes[-1] if closes else None
    sma_fast = sma(closes, 9)
    sma_slow = sma(closes, 21)
    rsi = compute_rsi(closes, 14)
    signals = []
    if sma_fast and sma_slow:
        # check last two values for crossover
        if len(closes) >= 22:
            prev_fast = sma(closes[:-1], 9)
            prev_slow = sma(closes[:-1], 21)
            if prev_fast is not None and prev_slow is not None:
                if prev_fast < prev_slow and sma_fast > sma_slow:
                    signals.append({"type":"sma_cross", "side":"buy", "reason":"fast crossed above slow"})
                elif prev_fast > prev_slow and sma_fast < sma_slow:
                    signals.append({"type":"sma_cross", "side":"sell", "reason":"fast crossed below slow"})
    if rsi is not None:
        if rsi < 30:
            signals.append({"type":"rsi", "side":"buy", "value": rsi, "reason":"oversold"})
        elif rsi > 70:
            signals.append({"type":"rsi", "side":"sell", "value": rsi, "reason":"overbought"})
    return {
        "latest_price": latest,
        "sma_fast": sma_fast,
        "sma_slow": sma_slow,
        "rsi": rsi,
        "signals": signals
    }

# ---------- Telegram utility ----------
def send_telegram_message(text: str) -> Dict[str,Any]:
    if not TELEGRAM_TOKEN or not TELEGRAM_CHAT:
        return {"_error":"telegram_not_configured"}
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    data = {"chat_id": TELEGRAM_CHAT, "text": text}
    try:
        r = requests.post(url, data=data, timeout=8)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"_error": str(e)}

# ---------- FastAPI endpoints ----------
class CandlesRequest(BaseModel):
    symbol: str
    interval: Optional[str] = "1min"
    outputsize: Optional[int] = 150

@app.post("/ict/candles")
def api_candles(req: CandlesRequest):
    res = fetch_candles_with_failover(req.symbol, interval=req.interval, outputsize=req.outputsize)
    if res.get("provider") is None:
        raise HTTPException(status_code=502, detail=res.get("error"))
    return res

class SignalsRequest(CandlesRequest):
    alert_telegram: Optional[bool] = False
    alert_text: Optional[str] = None

@app.post("/ict/signals")
def api_signals(req: SignalsRequest):
    res = fetch_candles_with_failover(req.symbol, interval=req.interval, outputsize=req.outputsize)
    if res.get("provider") is None:
        raise HTTPException(status_code=502, detail=res.get("error"))
    candles = res["candles"]
    sig = compute_ict_signals(candles)
    out = {"provider": res["provider"], "signals": sig}
    if req.alert_telegram:
        text = req.alert_text or f"ICT signals for {req.symbol}: {sig['signals']}"
        t = send_telegram_message(text)
        out["telegram"] = t
    return out

@app.get("/health")
def health():
    return {"status":"ok", "providers": {"twelvedata": bool(TWELVEDATA_KEY), "finnhub": bool(FINNHUB_KEY), "alphavantage": bool(ALPHAVANTAGE_KEY)}}
