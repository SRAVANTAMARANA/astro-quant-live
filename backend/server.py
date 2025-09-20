import os
import logging
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import requests

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
        "parse_mode": parse_mode
    }
    resp = requests.post(url, json=payload, timeout=15)
    try:
        data = resp.json()
    except ValueError:
        raise RuntimeError(f"Telegram returned non-json: {resp.text}")
    if not resp.ok or not data.get("ok", False):
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
        data = send_telegram_message(req.text)
    except Exception as e:
        logger.exception("telegram send failed")
        raise HTTPException(status_code=500, detail=str(e))
    return {"result": data}
