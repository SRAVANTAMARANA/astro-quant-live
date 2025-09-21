# backend/server.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# import the router that does the TwelveData fetch + forward
from twelvedata_api import router as tw_router

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
