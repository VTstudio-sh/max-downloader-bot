import os
import time
import threading
from flask import Flask
import requests

# Инициализация веб-сервера для Render (чтобы Web Service не падала)
app = Flask(__name__)

@app.route('/')
def health_check():
    return "MAX Bot is alive!", 200

TOKEN = os.environ.get("MAX_BOT_TOKEN")
API_URL = f"https://api.max.ru/bot{TOKEN}" if TOKEN else ""

COBALT_APIS = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.kwiatek.xyz/api/json",
    "https://api.hyper.lol/api/json"
]

def get_media_url(url):
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    payload = {
        "url": url,
        "videoQuality": "720"
    }
    
    for api in COBALT_APIS:
        try:
            res = requests.post(api, json=payload, headers=headers, timeout=12)
            data = res.json()
            if "url" in data:
                return data["url"]
            elif "picker" in data:
                return [item["url"] for item in data["picker"]]
        except Exception:
            continue
    return None

def send_message(chat_id, text):
    if not API_URL:
        return
    try:
        requests.post(f"{API_URL}/sendMessage", json={
            "chat_id": chat_id,
            "text": text
        }, timeout=10)
    except Exception as e:
        print(f"Error sending message: {e}")

def get_updates(offset=None):
    if not API_URL:
        return []
    try:
        res = requests.get(f"{API_URL}/getUpdates", params={"offset": offset, "timeout": 20}, timeout=25)
        data = res.json()
        if data.get("ok"):
            return data.get("result", [])
    except Exception:
        pass
    return []

def bot_loop():
    print("Бот МАКС запущен...")
    offset = None
    while True:
        updates = get_updates(offset)
        for update in updates:
            offset = update["update_id"] + 1
            message = update.get("message", {})
            text = message.get("text", "").strip()
            chat_id = message.get("chat", {}).get("id")

            if not chat_id or not text:
                continue

            if text.startswith("/start"):
                send_message(chat_id, "Привет! Пришли мне ссылку на видео или фото из VK, YouTube, Instagram, Pinterest или TikTok, и я её скачаю.")
                continue

            if not text.startswith(("http://", "https://")):
                send_message(chat_id, "Отправь корректную ссылку на видео или фото.")
                continue

            send_message(chat_id, "🔄 Обрабатываю ссылку...")
            media_result = get_media_url(text)

            if not media_result:
                send_message(chat_id, "❌ Не удалось обработать эту ссылку.")
                continue

            if isinstance(media_result, list):
                send_message(chat_id, f"✅ Найдено файлов: {len(media_result)}. Вот ссылки:\n" + "\n".join(media_result[:5]))
            else:
                send_message(chat_id, f"📥 Твоя ссылка на скачивание:\n{media_result}")
        
        time.sleep(1)

# Запуск бота в отдельном потоке
threading.Thread(target=bot_loop, daemon=True).start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
