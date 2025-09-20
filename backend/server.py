from fastapi import FastAPI
from pydantic import BaseModel
from typing import List

app = FastAPI()

# ----- Health Check -----
@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/hello")
async def hello():
    return {"message": "AstroQuant backend running"}

# ----- ICT Models -----
class PriceData(BaseModel):
    time: str
    open: float
    high: float
    low: float
    close: float

class CandleRequest(BaseModel):
    candles: List[PriceData]

@app.post("/ict/fvg")
async def detect_fvg(req: CandleRequest):
    candles = req.candles
    signals = []
    for i in range(2, len(candles)):
        prev = candles[i-2]
        curr = candles[i]
        if curr.low > prev.high:  # Bullish FVG
            signals.append({"time": curr.time, "type": "bullish"})
        if curr.high < prev.low:  # Bearish FVG
            signals.append({"time": curr.time, "type": "bearish"})
    return {"fvg_signals": signals}

@app.post("/ict/turtle_soup")
async def detect_turtle_soup(req: CandleRequest):
    candles = req.candles
    signals = []
    for i in range(1, len(candles)):
        prev = candles[i-1]
        curr = candles[i]
        if curr.low < prev.low and curr.close > prev.low:  # Bullish Turtle Soup
            signals.append({"time": curr.time, "type": "bullish"})
        if curr.high > prev.high and curr.close < prev.high:  # Bearish Turtle Soup
            signals.append({"time": curr.time, "type": "bearish"})
    return {"turtle_soup_signals": signals}
