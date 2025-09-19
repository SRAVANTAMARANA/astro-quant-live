# backend/server.py
# Simple FastAPI backend for AstroQuant demo:
# - /candles   -> returns last N historical candles (JSON)
# - /health    -> health check
# - websocket  -> ws feed that pushes new ticks (simulated if no live exchange)
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
import asyncio, uvicorn, os, time, random, json
from typing import List, Dict

app = FastAPI()

# Simple in-memory candle store (minute candles)
CANDLES: List[Dict] = []

# Seed with synthetic or basic historical values on startup
def seed_data():
    global CANDLES
    # If you have real CSV or DB you can load here. For now build synthetic walk.
    now = int(time.time())
    # create 120 minute candles
    base = 500.0
    CANDLES = []
    for i in range(120):
        t = now - (119 - i) * 60
        # random walk
        base += (random.random() - 0.45) * 1.2
        o = round(base + (random.random() - 0.5) * 0.3, 3)
        c = round(base + (random.random() - 0.5) * 0.3, 3)
        h = max(o, c) + round(random.random() * 0.3, 3)
        l = min(o, c) - round(random.random() * 0.3, 3)
        CANDLES.append({"t": t, "open": o, "high": h, "low": l, "close": c})
seed_data()

@app.get("/health")
async def health():
    return JSONResponse({"status":"ok"})

@app.get("/candles")
async def candles(limit: int = 80):
    # return last `limit` candles as JSON, timestamps ISO
    out = CANDLES[-limit:]
    return JSONResponse([{"t": c["t"], "close": c["close"], "open": c["open"], "high": c["high"], "low": c["low"]} for c in out])

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active: List[WebSocket] = []
    async def connect(self, ws: WebSocket):
        await ws.accept()
        self.active.append(ws)
    def disconnect(self, ws: WebSocket):
        if ws in self.active:
            self.active.remove(ws)
    async def broadcast(self, message: str):
        for conn in list(self.active):
            try:
                await conn.send_text(message)
            except:
                self.disconnect(conn)

manager = ConnectionManager()

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # keep connection alive; we don't expect client messages here
            await asyncio.sleep(1)
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task: simulate incoming tick each 5s and update last candle (or rotate new candle each minute)
async def tick_generator_loop():
    global CANDLES
    while True:
        # simulate small tick change
        last = CANDLES[-1]
        new_close = round(last["close"] + (random.random() - 0.5) * 0.6, 3)
        now = int(time.time())
        # update last candle's close/high/low
        last["close"] = new_close
        if new_close > last["high"]:
            last["high"] = new_close
        if new_close < last["low"]:
            last["low"] = new_close
        last["t"] = now  # update timestamp to latest tick time
        # Broadcast minimal payload (timestamp, close)
        payload = {"t": now, "close": new_close}
        await manager.broadcast(json.dumps(payload))
        # every 60s, push a new candle (rotate)
        await asyncio.sleep(5)

# Run background tick generator on startup
@app.on_event("startup")
async def startup_event():
    loop = asyncio.get_event_loop()
    loop.create_task(tick_generator_loop())

# If running standalone
if __name__ == "__main__":
    uvicorn.run("backend.server:app", host="0.0.0.0", port=int(os.environ.get("PORT", "10000")), reload=False)
