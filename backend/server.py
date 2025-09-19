# backend/server.py
import os
import logging
from fastapi import FastAPI, HTTPException
import requests
from pydantic import BaseModel

logger = logging.getLogger("uvicorn.error")
app = FastAPI(title="AstroQuant Backend")

# environment names expected on Render
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

TELEGRAM_API_BASE = "https://api.telegram.org/bot{token}/{method}"

def send_telegram_message(text: str, parse_mode: str = "HTML"):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        raise RuntimeError("Telegram bot token or chat id not configured in environment")
    url = TELEGRAM_API_BASE.format(token=TELEGRAM_BOT_TOKEN, method="sendMessage")
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": parse_mode,
    }
    resp = requests.post(url, json=payload, timeout=15)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"Telegram returned non-json: {resp.text}")
    if not resp.ok or not data.get("ok"):
        raise RuntimeError(f"Telegram API error: {data}")
    return data

class NotifyRequest(BaseModel):
    text: str

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.post("/notify")
async def notify(req: NotifyRequest):
    try:
        result = send_telegram_message(req.text)
    except Exception as e:
        logger.exception("Failed to send telegram message")
        raise HTTPException(status_code=500, detail=str(e))
    return {"status": "sent", "result": result}

# quick test endpoint to trigger a simple sample message (safe for testing)
@app.post("/alerts/test")
async def alerts_test():
    try:
        data = send_telegram_message("AstroQuant test alert ✅")
    except Exception as e:
        logger.exception("alerts/test failed")
        raise HTTPException(status_code=500, detail=str(e))
    return {"ok": True, "telegram": data}

# local runner (useful for local testing)
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.server:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)), reload=True)
