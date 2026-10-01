import os
import requests
from max_bot import Bot, Message

TOKEN = os.environ.get("MAX_BOT_TOKEN")
bot = Bot(token=TOKEN)

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

@bot.on_message()
def handle_message(message: Message):
    text = message.text.strip() if message.text else ""

    if text.startswith("/start"):
        message.reply("Привет! Пришли мне ссылку на видео или фото из VK, YouTube, Instagram, Pinterest или TikTok, и я её скачаю.")
        return

    if not text.startswith(("http://", "https://")):
        message.reply("Отправь корректную ссылку на видео или фото.")
        return

    message.reply("🔄 Обрабатываю ссылку...")
    media_result = get_media_url(text)

    if not media_result:
        message.reply("❌ Не удалось обработать эту ссылку.")
        return

    if isinstance(media_result, list):
        message.reply(f"✅ Найдено файлов: {len(media_result)}. Вот прямые ссылки для скачивания:\n" + "\n".join(media_result[:5]))
    else:
        message.reply(f"📥 Твоя ссылка на скачивание:\n{media_result}")

if __name__ == "__main__":
    print("Бот МАКС запущен...")
    bot.start_polling()
