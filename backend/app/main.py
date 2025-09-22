from fastapi import FastAPI, Query, HTTPException
import asyncio
from app.providers import fetch_candles
from app.signals import compute_all_signals
from app.ict_models import compute_all_ict_models
from app.mentor import generate_narrative
from app.alerts import send_telegram

app = FastAPI(title="AstroQuant ICT Panel")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/ict/candles")
async def get_candles(symbol: str, interval: str = "1min", limit: int = 50):
    result = await fetch_candles(symbol, interval, limit)
    if result.get("candles"):
        return {"status":"ok","provider": result.get("provider"), "candles": result["candles"]}
    raise HTTPException(status_code=404, detail="No data")

@app.post("/ict/signals")
async def get_signals(symbol: str, interval: str = "1min", limit: int = 200, alert: bool = Query(False)):
    res = await fetch_candles(symbol, interval, limit)
    candles = res.get("candles", [])
    signals = compute_all_signals(candles)
    models = compute_all_ict_models(candles)
    merged = {**signals, **models}
    if alert:
        text = generate_narrative(merged, symbol)
        asyncio.create_task(send_telegram(text))
    return {"status":"ok","provider":res.get("provider"),"signals":merged,"candles_count":len(candles)}

@app.post("/ict/mentor")
async def mentor(symbol: str, interval: str = "1min", limit: int = 200):
    res = await fetch_candles(symbol, interval, limit)
    candles = res.get("candles", [])
    signals = compute_all_signals(candles)
    models = compute_all_ict_models(candles)
    narrative = generate_narrative({**signals, **models}, symbol)
    return {"status":"ok","narrative": narrative}
