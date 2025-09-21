import os
import requests

API_KEY = os.getenv("TWELVEDATA_API_KEY")
BASE_URL = "https://api.twelvedata.com/time_series"

def fetch_data(symbol="XAU/USD", interval="5min", outputsize=50):
    url = f"{BASE_URL}?symbol={symbol}&interval={interval}&apikey={API_KEY}&outputsize={outputsize}"
    r = requests.get(url)
    r.raise_for_status()
    data = r.json()
    return data.get("values", [])

if __name__ == "__main__":
    candles = fetch_data()
    print(f"Fetched {len(candles)} candles from TwelveData")

    formatted = []
    for c in candles[::-1]:
        formatted.append({
            "time": c["datetime"],
            "open": float(c["open"]),
            "high": float(c["high"]),
            "low": float(c["low"]),
            "close": float(c["close"])
        })

    res = requests.post("http://localhost:8000/ict/fvg", json={
        "symbol": "XAUUSD",
        "interval": "5m",
        "candles": formatted
    })
    print(res.json())
