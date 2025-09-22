from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import requests
import os

app = FastAPI()

# Allow all origins for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# === API Keys (inline, no .env) ===
ALPHAVANTAGE_API_KEY = "II1CFA2DEF29VF2P"
TWELVEDATA_API_KEY = "55a08a202ca740589278abe23d94436a"

# === Helper: Fetch candles ===
def fetch_candles(symbol: str, interval: str = "1min", limit: int = 100):
    try:
        if "USD" in symbol or "XAU" in symbol:
            url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_API_KEY}&outputsize={limit}"
            r = requests.get(url)
            data = r.json()
            if "values" in data:
                return list(reversed(data["values"]))
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={ALPHAVANTAGE_API_KEY}"
        r = requests.get(url)
        data = r.json()
        key = f"Time Series ({interval})"
        if key in data:
            candles = [
                {
                    "datetime": t,
                    "open": v["1. open"],
                    "high": v["2. high"],
                    "low": v["3. low"],
                    "close": v["4. close"],
                }
                for t, v in data[key].items()
            ]
            return list(reversed(candles))
    except Exception as e:
        return {"error": str(e)}
    return []

# === ICT signal generator ===
def ict_signals(candles):
    signals = []
    for i in range(2, len(candles)):
        c1, c2 = candles[i-1], candles[i]
        # Turtle Soup (sweep of liquidity)
        if float(c1["low"]) < float(c2["low"]) and float(c1["low"]) == min(float(x["low"]) for x in candles[i-3:i]):
            signals.append({"time": c2["datetime"], "type": "BUY", "model": "Turtle Soup"})
        if float(c1["high"]) > float(c2["high"]) and float(c1["high"]) == max(float(x["high"]) for x in candles[i-3:i]):
            signals.append({"time": c2["datetime"], "type": "SELL", "model": "Turtle Soup"})
        # Fair Value Gap (FVG)
        if float(candles[i-2]["high"]) < float(candles[i]["low"]):
            signals.append({"time": c2["datetime"], "type": "BUY", "model": "FVG"})
        if float(candles[i-2]["low"]) > float(candles[i]["high"]):
            signals.append({"time": c2["datetime"], "type": "SELL", "model": "FVG"})
    return signals

# === AI Mentor Narrative ===
def build_narrative(signals):
    if not signals:
        return "No strong ICT signals detected yet. Stay patient."
    lines = []
    for sig in signals[-5:]:
        lines.append(f"{sig['time']} → {sig['model']} suggests {sig['type']}")
    return " | ".join(lines)

@app.post("/ict/candles")
async def get_candles(req: Request):
    body = await req.json()
    symbol = body.get("symbol", "XAU/USD")
    interval = body.get("interval", "1min")
    limit = int(body.get("limit", 50))
    candles = fetch_candles(symbol, interval, limit)
    return {"candles": candles}

@app.post("/ict/signals")
async def get_signals(req: Request):
    body = await req.json()
    symbol = body.get("symbol", "XAU/USD")
    interval = body.get("interval", "1min")
    limit = int(body.get("limit", 100))
    candles = fetch_candles(symbol, interval, limit)
    signals = ict_signals(candles)
    narrative = build_narrative(signals)
    return {"signals": signals, "narrative": narrative}
