import os, httpx

ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")

async def fetch_candles(symbol: str, interval: str = "5m"):
    url = f"https://api.twelvedata.com/time_series?symbol={symbol}&interval={interval}&apikey={TWELVEDATA_KEY}"
    async with httpx.AsyncClient() as client:
        r = await client.get(url)
        return r.json()
