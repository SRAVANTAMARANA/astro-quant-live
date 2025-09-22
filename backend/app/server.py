from fastapi import FastAPI, Query
import requests
import os

app = FastAPI()

# API keys (already in .env or replace directly here for testing)
ALPHA_KEY = os.getenv("ALPHAVANTAGE_API_KEY", "II1CFA2DEF29VF2P")
TWELVE_KEY = os.getenv("TWELVEDATA_API_KEY", "your_twelve_key_here")

@app.get("/ict/candles")
def get_candles(
    symbol: str = Query(..., description="Trading pair e.g. XAU/USD, BTC/USD, EUR/USD"),
    interval: str = Query("1min", description="Candle interval"),
    limit: int = Query(100, description="Number of candles")
):
    """
    Fetch candles from TwelveData first, fallback to AlphaVantage.
    """
    try:
        # Try TwelveData
        url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVE_KEY}&outputsize={limit}"
        r = requests.get(url)
        data = r.json()
        if "values" in data:
            return {"source": "twelvedata", "candles": data["values"]}

        # Fallback: AlphaVantage
        url = f"https://www.alphavantage.co/query?function=TIME_SERIES_INTRADAY&symbol={symbol}&interval={interval}&apikey={ALPHA_KEY}"
        r = requests.get(url)
        data = r.json()
        return {"source": "alphavantage", "candles": data}

    except Exception as e:
        return {"error": str(e)}
