import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

# Токен из настроек Render (MAX_BOT_TOKEN)
TOKEN = os.environ.get("MAX_BOT_TOKEN")

# Официальный базовый URL API МАКС
BASE_URL = "https://platform-api2.max.ru"

# URL вебхука вашего сервера на Render
WEBHOOK_URL = "https://max-downloader-bot.onrender.com/webhook"

COBALT_APIS = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.kwiatek.xyz/api/json",
    "https://api.hyper.lol/api/json"
]

def get_headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json"
    }

def set_webhook_auto():
    """Автоматическая привязка вебхука через правильный метод MAX API"""
    if not TOKEN:
        print("❌ Ошибка: Переменная MAX_BOT_TOKEN не найдена!")
        return
    
    url = f"{BASE_URL}/subscriptions"
    payload = {
        "url": WEBHOOK_URL
    }
    
    try:
        res = requests.post(url, json=payload, headers=get_headers(), timeout=10)
        print(f"Подключение Webhook: status {res.status_code}, response: {res.text}")
    except Exception as e:
        print(f"Ошибка подписки на Webhook: {e}")

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
    if not TOKEN or not chat_id:
        return
    
    url = f"{BASE_URL}/messages"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    
    try:
        res = requests.post(url, json=payload, headers=get_headers(), timeout=10)
        print(f"Отправка сообщения: status {res.status_code}, response: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")

@app.route('/', methods=['GET'])
def health_check():
    return "MAX Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    print(f"📥 Входящие данные от МАКС: {data}")
    
    # Разбор структуры сообщений МАКС
    message = data.get("message") or data.get("object", {})
    text = (message.get("text") or message.get("body", "")).strip()
    
    chat_id = message.get("chat_id") or message.get("chat", {}).get("id") or message.get("recipient", {}).get("chat_id")

    if chat_id and text:
        if text.startswith("/start"):
            send_message(chat_id, "Привет! Пришли мне ссылку на видео или фото из VK, YouTube, Instagram, Pinterest или TikTok, и я её скачаю.")
        elif not text.startswith(("http://", "https://")):
            send_message(chat_id, "Отправь корректную ссылку на видео или фото.")
        else:
            send_message(chat_id, "🔄 Обрабатываю ссылку...")
            media_result = get_media_url(text)

            if not media_result:
                send_message(chat_id, "❌ Не удалось обработать эту ссылку.")
            elif isinstance(media_result, list):
                send_message(chat_id, f"✅ Найдено файлов: {len(media_result)}.\n" + "\n".join(media_result[:5]))
            else:
                send_message(chat_id, f"📥 Твоя ссылка на скачивание:\n{media_result}")

    return jsonify({"status": "ok"}), 200

# Автоустановка вебхука при старте
set_webhook_auto()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
