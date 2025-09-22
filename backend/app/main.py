from fastapi import FastAPI, Body
from fastapi.middleware.cors import CORSMiddleware
from .providers import get_candles

app = FastAPI(title="AstroQuant ICT Panel")

# Allow frontend access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten later
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.post("/ict/candles")
def ict_candles(
    payload: dict = Body(..., example={"symbol": "BTC/USD", "interval": "1min", "limit": 50})
):
    symbol = payload.get("symbol", "BTC/USD")
    interval = payload.get("interval", "1min")
    limit = payload.get("limit", 50)

    data = get_candles(symbol, interval, limit)
    return data

@app.post("/ict/signals")
def ict_signals(
    payload: dict = Body(..., example={"symbol": "BTC/USD", "interval": "1min", "limit": 50})
):
    """
    Placeholder for ICT signal detection (Turtle Soup, FVG, etc.).
    Right now it just reuses candles.
    """
    symbol = payload.get("symbol", "BTC/USD")
    interval = payload.get("interval", "1min")
    limit = payload.get("limit", 50)

    candles = get_candles(symbol, interval, limit)
    return {"signals": [], "candles": candles}

@app.post("/ict/mentor")
def ict_mentor(
    payload: dict = Body(..., example={"symbol": "BTC/USD", "interval": "1min"})
):
    """
    AI Mentor placeholder — later will analyze ICT models & suggest trades.
    """
    symbol = payload.get("symbol", "BTC/USD")
    interval = payload.get("interval", "1min")

    return {
        "mentor": f"For {symbol} on {interval}, follow ICT rules and watch for liquidity sweeps.",
        "status": "ok",
    }
