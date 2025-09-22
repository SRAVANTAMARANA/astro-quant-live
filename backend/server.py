from fastapi import FastAPI
from proxy_candles import router as proxy_candles_router

app = FastAPI(
    title="AstroQuant ICT Backend",
    description="Backend service for ICT charting & signals",
    version="0.1.0"
)

# Attach ICT candles router
app.include_router(proxy_candles_router, prefix="/ict")

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/hello")
async def hello():
    return {"msg": "Hello from AstroQuant ICT backend"}
