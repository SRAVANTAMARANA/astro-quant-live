from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Allow frontend (localhost:3000) to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Example API endpoint
@app.get("/signals")
def get_signals():
    return {
        "signals": [
            {"time": "2025-09-21T10:00:00", "symbol": "XAUUSD", "type": "buy", "price": 1945.2},
            {"time": "2025-09-21T14:00:00", "symbol": "XAUUSD", "type": "sell", "price": 1952.7},
        ]
    }           
