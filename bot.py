import os
import time
import requests
import urllib3
import yt_dlp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://platform-api2.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def send_message_with_button(chat_id, text, button_text, button_url):
    try:
        params = {"user_id": chat_id}
        
        # Пробуем стандартный формат инлайн-кнопок для платформ такого типа
        data = {
            "text": text,
            "inline_keyboard": [
                [
                    {
                        "text": button_text,
                        "url": button_url
                    }
                ]
            ]
        }
        
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=data, verify=False, timeout=15)
        print(f"Ответ сервера с кнопкой (chat_id={chat_id}): статус {res.status_code}, тело: {res.text}")
        
        # Если API выдаст ошибку из-за формата клавиатуры, отправим хотя бы текст со ссылкой резервом
        if res.status_code != 200:
            data_fallback = {"text": f"{text}\n\n🔗 {button_url}"}
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=data_fallback, verify=False, timeout=15)
            
    except Exception as e:
        print(f"Ошибка отправки сообщения с кнопкой: {e}")

def process_smart_video(chat_id, video_url):
    ydl_opts_optimal = {
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        # Отправляем текстовый статус
        params = {"user_id": chat_id}
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json={"text": "⚡ Получаю прямую ссылку на файл..."}, verify=False, timeout=15)
        
        with yt_dlp.YoutubeDL(ydl_opts_optimal) as ydl:
            info = ydl.extract_info(video_url, download=False)
            direct_url = info.get('url')
            
        if direct_url:
            # Отправляем сообщение с красивой инлайн-кнопкой
            send_message_with_button(
                chat_id, 
                "✅ Видео успешно обработано! Нажмите на кнопку ниже, чтобы скачать файл:", 
                "📥 Скачать видео", 
                direct_url
            )
        else:
            send_message_with_button(chat_id, "❌ Не удалось получить прямую ссылку на видео.", "Открыть оригинал", video_url)
                
    except Exception as e:
        print(f"Ошибка обработки: {e}")
        send_message_with_button(chat_id, f"❌ Произошла ошибка при обработке ссылки: {e}", "Повторить", video_url)

def main():
    print("Бот запущен и настроен на выдачу кнопок...")
    current_marker = None

    while True:
        try:
            params = {'timeout': 30}
            if current_marker:
                params['marker'] = current_marker
                
            response = requests.get(
                f"{BASE_URL}/updates", 
                headers=HEADERS, 
                params=params,
                verify=False,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                if "marker" in data:
                    current_marker = data["marker"]
                
                for update in data.get("updates", []):
                    message = update.get("message", {})
                    
                    chat_id = (
                        message.get("chat_id") or
                        message.get("sender", {}).get("user_id") or
                        message.get("from", {}).get("id") or
                        message.get("chat", {}).get("id") or
                        message.get("recipient", {}).get("chat_id")
                    )
                    
                    body = message.get("body", {})
                    text = body.get("text") or message.get("text", "")
                    
                    if chat_id and text and "http" in text:
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        process_smart_video(chat_id, url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
