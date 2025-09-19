# backend/ict_server.py
import os, time
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from ict_detector import detect_all, get_events, ack_event, log_event

app = FastAPI(title="AstroQuant ICT Server")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

CANDLE_CACHE = {}

@app.get("/health")
async def health():
    return {"status":"ok"}

@app.get("/api/ict/signals")
async def api_ict_signals(symbol: str = Query(..., min_length=1), limit: int = 300):
    sym = symbol.upper()
    candles = CANDLE_CACHE.get(sym)
    if not candles:
        raise HTTPException(status_code=404, detail="No candles cached for symbol. Call /api/ohlc first or ensure backend fetcher seeds candles.")
    result = detect_all(candles[-limit:], symbol=sym)
    return {"status":"ok","symbol":sym,"result":result}

@app.get("/api/ict/narrative")
async def api_ict_narrative(symbol: str = Query(..., min_length=1)):
    sym = symbol.upper()
    candles = CANDLE_CACHE.get(sym, [])
    events = get_events(sym, since_ts=int(time.time()) - 86400)
    bullets=[]
    if len(candles) >= 50:
        closes = [c['close'] for c in candles]
        ma50 = sum(closes[-50:]) / 50
        last = closes[-1]
        bias = "Bullish" if last > ma50 else "Bearish"
    else:
        bias = "Neutral"
    bullets.append(f"HTF Bias: {bias} (simple MA50 check)")
    res = {}
    try:
        res = detect_all(candles[-300:], symbol=sym)
    except Exception as e:
        res = {}
    cand = res.get("candidates", [])
    if cand:
        for c in cand:
            bullets.append(f"Candidate: {c['side'].upper()} entry@{c['entry']} stop@{c['stop']} tgt@{c['target']} RR={c['rr']}")
    else:
        bullets.append("No solid OB candidate found in recent candles.")
    today_events = [e for e in events if e['ts'] >= int(time.time()) - 86400]
    bullets.append(f"Detected events today: {len(today_events)}")
    if today_events:
        avg_conf = sum(e['confidence'] for e in today_events)/len(today_events)
        bullets.append(f"Model average confidence (24h): {round(avg_conf,2)}")
    bullets.append("AI note: send POST /api/ict/ack with {event_id, outcome:'win'|'loss'} to improve model calibration.")
    return {"status":"ok","symbol":sym,"narrative": bullets}

@app.get("/api/ict/stats")
async def api_ict_stats(symbol: str = Query(..., min_length=1)):
    sym = symbol.upper()
    events = get_events(sym, since_ts=int(time.time()) - 86400)
    total = len(events)
    wins = len([e for e in events if e.get("outcome")=="win"])
    losses = len([e for e in events if e.get("outcome")=="loss"])
    unresolved = len([e for e in events if not e.get("outcome")])
    return {"status":"ok","symbol":sym,"total":total,"wins":wins,"losses":losses,"unresolved":unresolved,"events":events}

from pydantic import BaseModel
class AckModel(BaseModel):
    event_id: int
    outcome: str

@app.post("/api/ict/ack")
async def api_ict_ack(payload: AckModel):
    ack_event(payload.event_id, payload.outcome)
    return {"status":"ok","ack":True}