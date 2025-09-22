# backend/server.py
# near your other imports
from fastapi import FastAPI
from .proxy_candles import router as proxy_candles_router
app = FastAPI()
app.include_router(proxy_candles_router)
app = FastAPI(title="AstroQuant backend (minimal)")
# allow CORS from your frontend if needed (adjust origins)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # change to your frontend origin in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# include the TwelveData router
app.include_router(tw_router, prefix="")

@app.get("/health")
def health():
    return {"status": "ok"}
