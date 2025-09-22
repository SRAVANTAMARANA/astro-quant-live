import os, httpx
BOT = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT = os.getenv("TELEGRAM_CHAT_ID")

async def send_telegram(text: str):
    if not BOT or not CHAT: return False
    url = f"https://api.telegram.org/bot{BOT}/sendMessage"
    payload = {"chat_id": CHAT, "text": text}
    async with httpx.AsyncClient() as client:
        r = await client.post(url, json=payload)
    return r.status_code == 200
