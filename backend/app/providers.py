import os
import requests

ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

def fetch_from_alphavantage(symbol="BTC/USD", interval="1min", limit=50):
    try:
        url = (
            f"https://www.alphavantage.co/query?"
            f"function=CRYPTO_INTRADAY&symbol=BTC&market=USD&interval={interval}&apikey={ALPHAVANTAGE_KEY}"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        if "Time Series Crypto" in data:
            candles = []
            for ts, v in list(data["Time Series Crypto ("+interval+")"].items())[:limit]:
                candles.append({
                    "datetime": ts,
                    "open": float(v["1. open"]),
                    "high": float(v["2. high"]),
                    "low": float(v["3. low"]),
                    "close": float(v["4. close"]),
                })
            return candles
    except Exception as e:
        print("AlphaVantage error:", e)
    return None


def fetch_from_twelvedata(symbol="BTC/USD", interval="1min", limit=50):
    try:
        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={symbol}&interval={interval}&outputsize={limit}&apikey={TWELVEDATA_KEY}"
        )
        r = requests.get(url, timeout=10)
        data = r.json()
        if "values" in data:
            candles = []
            for v in data["values"]:
                candles.append({
                    "datetime": v["datetime"],
                    "open": float(v["open"]),
                    "high": float(v["high"]),
                    "low": float(v["low"]),
                    "close": float(v["close"]),
                })
            return candles
    except Exception as e:
        print("TwelveData error:", e)
    return None


def fetch_from_finnhub(symbol="BINANCE:BTCUSDT", limit=50):
    try:
        url = f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}"
        r = requests.get(url, timeout=10)
        data = r.json()
        if "c" in data and data["c"] is not None:
            return [{
                "datetime": "latest",
                "open": data["o"],
                "high": data["h"],
                "low": data["l"],
                "close": data["c"],
            }]
    except Exception as e:
        print("Finnhub error:", e)
    return None


def get_candles(symbol="BTC/USD", interval="1min", limit=50):
    # Try AlphaVantage first
    candles = fetch_from_alphavantage(symbol, interval, limit)
    if candles:
        return {"provider": "AlphaVantage", "candles": candles}

    # Fallback to TwelveData
    candles = fetch_from_twelvedata(symbol, interval, limit)
    if candles:
        return {"provider": "TwelveData", "candles": candles}

    # Fallback to Finnhub
    candles = fetch_from_finnhub()
    if candles:
        return {"provider": "Finnhub", "candles": candles}

    return {"error": "All providers failed"}
