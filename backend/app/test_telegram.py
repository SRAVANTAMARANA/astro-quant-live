import os
import requests

def send_telegram_test():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    chat_id = os.getenv("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        print("❌ TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set in .env")
        return

    url = f"https://api.telegram.org/bot{token}/sendMessage"
    text = "🚀 Test message from AstroQuant backend"

    resp = requests.post(url, data={"chat_id": chat_id, "text": text})

    print("Status:", resp.status_code)
    print("Response:", resp.text)

if __name__ == "__main__":
    send_telegram_test()
