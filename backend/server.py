# backend/server.py
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
from pathlib import Path
import math
import datetime

app = FastAPI(title="AstroQuant backend (serves frontend)")

# allow frontend to call APIs
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # restrict later to your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Path to repo root (Render runs from repo root). Mount "frontend" dir to root path.
FRONTEND_DIR = Path(__file__).resolve().parents[1] / "frontend"

# If frontend folder doesn't exist, app still runs.
if FRONTEND_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(FRONTEND_DIR)), name="static-files")
    # serve index at root
    @app.get("/", response_class=HTMLResponse)
    async def root():
        index_file = FRONTEND_DIR / "index.html"
        if index_file.exists():
            return FileResponse(str(index_file))
        return HTMLResponse("<h3>Frontend index.html not found in /frontend</h3>", status_code=404)
else:
    @app.get("/", response_class=HTMLResponse)
    async def root_no_frontend():
        return HTMLResponse("<h3>Frontend folder not found. Put frontend files in /frontend</h3>", status_code=404)


# Health endpoint
@app.get("/health")
async def health():
    return {"status": "ok", "time": datetime.datetime.utcnow().isoformat()}


# Demo: Gann conversion endpoint (price <-> degree/time)
@app.get("/gann/convert")
async def gann_convert(type: str = "price_to_degree", value: float = 100.0):
    """
    Example conversions (demo):
    - price_to_degree: simple map price -> degrees (0-360) using a wrap formula
    - degree_to_price: map degree -> price (reverse)
    - time_to_degree: map hours since epoch -> degree
    """
    try:
        if type == "price_to_degree":
            # map price to 0-360 using modulo and scaling demo
            degree = (value % 360) if value >= 0 else (360 + (value % 360))
            return {"type": type, "price": value, "degree": degree}
        elif type == "degree_to_price":
            # demo reverse: price = degree * some scale
            price = value * 1.5
            return {"type": type, "degree": value, "price": price}
        elif type == "time_to_degree":
            # value is unix timestamp
            degree = (value % 360)
            return {"type": type, "timestamp": value, "degree": degree}
        else:
            return {"error": "unknown type"}
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=400)


# Demo: ICT model detection (fake)
@app.post("/ict/detect")
async def ict_detect(payload: dict):
    """
    Receives chart-data-like payload (mock) and returns a fake detection result.
    Example payload: { "symbol": "AAPL", "candles": [[ts,open,high,low,close], ...] }
    """
    # For demo we return a fake detection
    symbol = payload.get("symbol", "UNKNOWN")
    sample = {
        "symbol": symbol,
        "detected_models": [
            {"name": "ICT Order Block", "confidence": 0.72},
            {"name": "Liquidity Run", "confidence": 0.45}
        ],
        "timestamp": datetime.datetime.utcnow().isoformat()
    }
    return sample


# Demo: Prediction endpoint (fake)
@app.post("/predict")
async def predict(payload: dict):
    """
    Dummy /predict: accepts {symbol, timeframe} and returns a sample prediction
    """
    symbol = payload.get("symbol", "SYMBOL")
    timeframe = payload.get("timeframe", "1h")
    result = {
        "symbol": symbol,
        "timeframe": timeframe,
        "prediction": {
            "direction": "up",
            "confidence": 0.63,
            "target_price": 123.45,
            "stop_price": 117.0
        },
        "note": "This is a demo prediction. Replace with real model output."
    }
    return result


# Basic error handler
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    return JSONResponse({"error": str(exc)}, status_code=500)
