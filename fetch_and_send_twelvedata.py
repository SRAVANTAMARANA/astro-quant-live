# backend/fetch_and_send_twelvedata.py
import os
import requests
import sys

API_KEY = os.getenv("TWELVEDATA_API_KEY")
if not API_KEY:
    print("TWELVEDATA_API_KEY not found in env")
    sys.exit(1)

BASE_URL = "https://api.twelvedata.com/time_series"

def fetch_data(symbol="XAU/USD", interval="5min", outputsize=50):
    url = f"{BASE_URL}?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}"
    r = requests.get(url, timeout=15)
    r.raise_for_status()
    data = r.json()
    # TwelveData returns "values" list
    return data.get("values", [])

def post_to_ict(formatted, symbol="XAUUSD", interval="5m"):
    payload = {
        "symbol": symbol,
        "interval": interval,
        "candles": formatted
    }
    # backend service runs on port 8000 and has /ict/fvg endpoint per repo
    resp = requests.post("http://localhost:8000/ict/fvg", json=payload, timeout=15)
    try:
        print("ict response:", resp.status_code, resp.text)
        return resp.json()
    except Exception:
        return {"status": resp.status_code, "text": resp.text}

if __name__ == "__main__":
    # optional args: symbol interval
    symbol = sys.argv[1] if len(sys.argv) > 1 else "XAU/USD"
    interval = sys.argv[2] if len(sys.argv) > 2 else "5min"
    values = fetch_data(symbol=symbol, interval=interval, outputsize=100)
    if not values:
        print("No candle data returned:", values)
        sys.exit(1)

    # TwelveData returns newest first; reverse to chronological asc if needed
    formatted = []
    for c in reversed(values):
        formatted.append({
            "time": c.get("datetime", c.get("timestamp")), 
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"])
        })

    print(f"Fetched {len(formatted)} candles. Posting to /ict/fvg ...")
    out = post_to_ict(formatted, symbol=symbol.replace("/", ""), interval=interval)
    print("Done:", out)
