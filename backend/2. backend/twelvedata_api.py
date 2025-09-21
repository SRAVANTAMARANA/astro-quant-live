# backend/twelvedata_api.py
import os
import typing as t
from fastapi import APIRouter, HTTPException, Query
import requests

router = APIRouter()

# Environment configuration
TWELVEDATA_KEY = os.getenv("TWELVEDATA_API_KEY")
# By default we assume the ICT endpoint is on the same backend host/port
# If ICT is in a different docker service change ICT_BASE_URL to http://<service>:<port>
ICT_BASE_URL = os.getenv("ICT_BASE_URL", "http://localhost:8000")
ICT_ENDPOINT = f"{ICT_BASE_URL}/ict/fvg"

def fetch_candles_from_twelvedata(symbol: str, interval: str = "5min", outputsize: int = 100) -> dict:
    if not TWELVEDATA_KEY:
        raise RuntimeError("TWELVEDATA_API_KEY env var not set")
    url = "https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": outputsize,
        "format": "JSON",
        "apikey": TWELVEDATA_KEY,
    }
    resp = requests.get(url, params=params, timeout=20)
    resp.raise_for_status()
    return resp.json()

def normalize_twelvedata(values: t.List[dict]) -> t.List[dict]:
    # TwelveData returns most-recent-first; reverse for oldest-first
    normalized = []
    for v in reversed(values):
        # defensive conversion
        normalized.append({
            "time": v.get("datetime") or v.get("timestamp") or v.get("time"),
            "open": float(v.get("open", 0)) if v.get("open") not in (None, "") else None,
            "high": float(v.get("high", 0)) if v.get("high") not in (None, "") else None,
            "low": float(v.get("low", 0)) if v.get("low") not in (None, "") else None,
            "close": float(v.get("close", 0)) if v.get("close") not in (None, "") else None,
            "volume": float(v.get("volume")) if v.get("volume") not in (None, "") else None,
        })
    return normalized

def post_to_ict(symbol: str, interval: str, candles: t.List[dict]) -> requests.Response:
    payload = {"symbol": symbol, "interval": interval, "candles": candles}
    resp = requests.post(ICT_ENDPOINT, json=payload, timeout=20)
    return resp

@router.post("/ict/fetch_twelvedata")
def fetch_and_forward(
    symbol: str = Query(..., description="Symbol to fetch. Example: XAU/USD or AAPL"),
    interval: str = Query("5min", description="Interval, e.g. 1min, 5min, 15min"),
    outputsize: int = Query(100, description="How many candles to fetch (max depends on TwelveData)"),
):
    """
    Fetches candles from TwelveData and forwards them to the ICT endpoint (/ict/fvg).
    Returns ICT response body and metadata.
    """
    try:
        if not TWELVEDATA_KEY:
            raise HTTPException(status_code=500, detail="TWELVEDATA_API_KEY not configured")

        tw_json = fetch_candles_from_twelvedata(symbol, interval, outputsize)
        if "values" not in tw_json:
            # forward the entire response from TwelveData in the error detail for debugging
            raise HTTPException(status_code=502, detail={"error": "twelvedata_missing_values", "body": tw_json})

        candles = normalize_twelvedata(tw_json["values"])
        ict_resp = post_to_ict(symbol, interval, candles)

        try:
            ict_body = ict_resp.json()
        except Exception:
            ict_body = ict_resp.text

        if ict_resp.status_code >= 400:
            raise HTTPException(status_code=502, detail={"ict_status": ict_resp.status_code, "ict_body": ict_body})

        return {
            "status": "ok",
            "symbol": symbol,
            "interval": interval,
            "candles_sent": len(candles),
            "ict_status": ict_resp.status_code,
            "ict_body": ict_body,
        }

    except requests.RequestException as e:
        raise HTTPException(status_code=502, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
