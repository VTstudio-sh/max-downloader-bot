import os
import requests
from flask import Flask, request, jsonify

app = Flask(__name__)

TOKEN = os.environ.get("MAX_BOT_TOKEN")
WEBHOOK_URL = "https://max-downloader-bot.onrender.com/webhook"

COBALT_APIS = [
    "https://api.cobalt.tools/api/json",
    "https://cobalt-api.kwiatek.xyz/api/json",
    "https://api.hyper.lol/api/json"
]

def set_webhook_auto():
    """Автоматическая привязка вебхука при старте"""
    if not TOKEN:
        print("❌ Ошибка: Переменная MAX_BOT_TOKEN не найдена!")
        return
    
    api_endpoints = [
        f"https://api.max.ru/bot{TOKEN}/setWebhook",
        f"https://api.max.ru/v1/bot{TOKEN}/setWebhook",
        f"https://platform.max.ru/api/bot{TOKEN}/setWebhook"
    ]
    
    for url in api_endpoints:
        try:
            res = requests.post(url, json={"url": WEBHOOK_URL}, timeout=5)
            print(f"Попытка привязки Webhook ({url}): status {res.status_code}, response: {res.text}")
            if res.status_code == 200:
                break
        except Exception as e:
            print(f"Ошибка запроса вебхука: {e}")

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
    if not TOKEN:
        return
    
    api_endpoints = [
        f"https://api.max.ru/bot{TOKEN}/sendMessage",
        f"https://api.max.ru/v1/bot{TOKEN}/sendMessage"
    ]
    
    for url in api_endpoints:
        try:
            res = requests.post(url, json={"chat_id": chat_id, "text": text}, timeout=10)
            if res.status_code == 200:
                break
        except Exception as e:
            print(f"Ошибка отправки сообщения: {e}")

@app.route('/', methods=['GET'])
def health_check():
    return "MAX Bot is alive!", 200

@app.route('/webhook', methods=['POST'])
def webhook():
    data = request.get_json(silent=True) or {}
    print(f"📥 Входящие данные от МАКС: {data}")
    
    message = data.get("message", {})
    text = message.get("text", "").strip()
    chat_id = message.get("chat", {}).get("id")

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

set_webhook_auto()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
