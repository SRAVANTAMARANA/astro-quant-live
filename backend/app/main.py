from fastapi import FastAPI, Query
from pydantic import BaseModel
from typing import List
import os, requests, datetime, pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

app = FastAPI(title="AstroQuant Apex")

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
SCHEDULE_ENABLE = os.getenv("SCHEDULE_ENABLE","true").lower() in ("1","true","yes")
SCHEDULE_HOUR = int(os.getenv("SCHEDULE_HOUR","9"))
SCHEDULE_MINUTE = int(os.getenv("SCHEDULE_MINUTE","0"))
SCHEDULE_TZ = os.getenv("SCHEDULE_TZ","Asia/Kolkata")

def send_to_telegram(text: str):
    if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
        return {"status":"no keys"}
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": text, "parse_mode":"HTML"}
    try:
        r = requests.post(url, json=payload, timeout=8)
        return {"status":"sent" if r.ok else "error", "http": r.status_code}
    except Exception as e:
        return {"status":"error", "error": str(e)}

class Signal(BaseModel):
    symbol: str
    signal: str
    strength: str
    note: str = ""

def demo_signals():
    return [
        {"symbol":"XAUUSD","signal":"BUY","strength":"high","note":"ICT momentum + astro confluence"},
        {"symbol":"EURUSD","signal":"SELL","strength":"medium","note":"mean reversion"}
    ]

def demo_news():
    now = datetime.datetime.utcnow().isoformat()+"Z"
    return [
        {"time": now, "headline":"Macro event impacts FX", "impact":"high"},
        {"time": now, "headline":"Planetary cycle confluence", "impact":"medium"}
    ]

@app.get("/health")
def health():
    return {"status":"ok"}

@app.get("/signals", response_model=List[Signal])
def get_signals():
    sigs = demo_signals()
    text = "🔔 <b>AstroQuant Signals</b>\n" + "".join([f"{s['symbol']} → {s['signal']} ({s['strength']})\n" for s in sigs])
    send_to_telegram(text)
    return sigs

@app.get("/send_custom")
def send_custom(msg: str):
    return send_to_telegram(f"📝 <b>Custom Msg</b>: {msg}")

def build_brief():
    sigs = demo_signals()
    news = demo_news()
    ts = datetime.datetime.now(pytz.timezone(SCHEDULE_TZ)).strftime("%Y-%m-%d %H:%M %Z")
    text = f"📊 <b>AstroQuant Daily Brief</b>\n{ts}\n\n<b>Signals:</b>\n"
    text += "".join([f"• {s['symbol']}: {s['signal']} ({s['strength']})\n" for s in sigs])
    text += "\n<b>News:</b>\n" + "".join([f"• {n['headline']} ({n['impact']})\n" for n in news])
    return text

def daily_job():
    msg = build_brief()
    send_to_telegram(msg)

scheduler=None
@app.on_event("startup")
def start_scheduler():
    global scheduler
    if not SCHEDULE_ENABLE: return
    tz = pytz.timezone(SCHEDULE_TZ)
    scheduler = BackgroundScheduler(timezone=tz)
    scheduler.add_job(daily_job, CronTrigger(hour=SCHEDULE_HOUR, minute=SCHEDULE_MINUTE, timezone=tz))
    scheduler.start()

@app.on_event("shutdown")
def stop_scheduler():
    global scheduler
    if scheduler: scheduler.shutdown(wait=False)
