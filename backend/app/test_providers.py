import os, requests, json

def test_finnhub():
    key = os.getenv("FINNHUB_API_KEY")
    url = "https://finnhub.io/api/v1/quote"
    params = {"symbol": "BINANCE:BTCUSDT", "token": key}
    resp = requests.get(url, params=params)
    return {"provider": "finnhub", "data": resp.json()}

def test_alphavantage():
    key = os.getenv("ALPHAVANTAGE_API_KEY")
    url = "https://www.alphavantage.co/query"
    params = {
        "function": "CURRENCY_EXCHANGE_RATE",
        "from_currency": "BTC",
        "to_currency": "USD",
        "apikey": key
    }
    resp = requests.get(url, params=params)
    return {"provider": "alphavantage", "data": resp.json()}

def test_twelvedata():
    key = os.getenv("TWELVEDATA_API_KEY")
    url = "https://api.twelvedata.com/price"
    params = {"symbol": "BTC/USD", "apikey": key}
    resp = requests.get(url, params=params)
    return {"provider": "twelvedata", "data": resp.json()}

if __name__ == "__main__":
    results = []
    try:
        results.append(test_finnhub())
    except Exception as e:
        results.append({"provider": "finnhub", "error": str(e)})
    try:
        results.append(test_alphavantage())
    except Exception as e:
        results.append({"provider": "alphavantage", "error": str(e)})
    try:
        results.append(test_twelvedata())
    except Exception as e:
        results.append({"provider": "twelvedata", "error": str(e)})

    print(json.dumps(results, indent=2))
