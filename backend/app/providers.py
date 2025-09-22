import os
import requests

ALPHAVANTAGE_KEY = os.getenv("ALPHAVANTAGE_API_KEY")
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY")

def normalize_symbol(symbol: str, provider: str) -> str:
    """
    Normalize symbol format depending on provider.
    """
    symbol = symbol.upper()

    if provider == "alphavantage":
        if symbol in ["BTC/USD", "BTCUSDT"]:
            return {"from": "BTC", "to": "USD"}
        if symbol in ["XAU/USD", "GOLD"]:
            return {"from": "XAU", "to": "USD"}
        if "/" in symbol:
            base, quote = symbol.split("/")
            return {"from": base, "to": quote}
    elif provider == "twelvedata":
        return symbol  # TwelveData accepts BTC/USD, XAU/USD, EUR/USD
    elif provider == "finnhub":
        if symbol in ["BTC/USD", "BTCUSDT"]:
            return "BINANCE:BTCUSDT"
        if symbol in ["XAU/USD", "GOLD"]:
            return "OANDA:XAU_USD"
        if symbol in ["EUR/USD"]:
            return "OANDA:EUR_USD"
    return symbol


def fetch_from_alphavantage(symbol="BTC/USD", interval="1min", limit=50):
    try:
        norm = normalize_symbol(symbol, "alphavantage")
        if isinstance(norm, dict) and norm["from"] == "BTC":
            # Crypto intraday
            url = (
                f"https://www.alphavantage.co/query?"
                f"function=CRYPTO_INTRADAY&symbol={norm['from']}&market={norm['to']}&interval={interval}&apikey={ALPHAVANTAGE_KEY}"
            )
        elif isinstance(norm, dict):
            # FX intraday
            url = (
                f"https://www.alphavantage.co/query?"
                f"function=FX_INTRADAY&from_symbol={norm['from']}&to_symbol={norm['to']}&interval={interval}&apikey={ALPHAVANTAGE_KEY}"
            )
        else:
            return None

        r = requests.get(url, timeout=10)
        data = r.json()
        for k in data.keys():
            if "Time Series" in k:
                candles = []
                for ts, v in list(data[k].items())[:limit]:
                    candles.append({
                        "datetime": ts,
                        "open": float(v.get("1. open", 0)),
                        "high": float(v.get("2. high", 0)),
                        "low": float(v.get("3. low", 0)),
                        "close": float(v.get("4. close", 0)),
                    })
                return candles
    except Exception as e:
        print("AlphaVantage error:", e)
    return None


def fetch_from_twelvedata(symbol="BTC/USD", interval="1min", limit=50):
    try:
        norm = normalize_symbol(symbol, "twelvedata")
        url = (
            f"https://api.twelvedata.com/time_series?"
            f"symbol={norm}&interval={interval}&outputsize={limit}&apikey={TWELVEDATA_KEY}"
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


def fetch_from_finnhub(symbol="BTC/USD", limit=50):
    try:
        norm = normalize_symbol(symbol, "finnhub")
        url = f"https://finnhub.io/api/v1/quote?symbol={norm}&token={FINNHUB_KEY}"
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
    candles = fetch_from_finnhub(symbol, limit)
    if candles:
        return {"provider": "Finnhub", "candles": candles}

    return {"error": "All providers failed"}
