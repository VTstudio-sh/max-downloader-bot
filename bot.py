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

def send_text(recipient_id, text):
    try:
        data = {
            "recipient": {
                "chat_id": str(recipient_id)
            },
            "text": text
        }
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False, timeout=15)
        print(f"Ответ сервера (chat_id={recipient_id}): статус {res.status_code}, тело: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки текста: {e}")

def process_smart_video(recipient_id, video_url):
    filename = f"video_{recipient_id}.mp4"
    
    ydl_opts_optimal = {
        'format': 'best[height<=720][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
        'concurrent_fragment_downloads': 4,
    }
    
    try:
        # Скачиваем видео для проверки
        with yt_dlp.YoutubeDL(ydl_opts_optimal) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Видео успешно обработано. Размер: {file_size:.2f} МБ")
            
            # Отправляем обратно чистую ссылку
            send_text(recipient_id, f"🔗 Ссылка на видео: {video_url}")
                
    except Exception as e:
        print(f"Ошибка обработки: {e}")
        send_text(recipient_id, f"❌ Ошибка: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот запущен и настроен на отправку ссылок...")
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
                    
                    recipient_id = (
                        message.get("chat", {}).get("chat_id") or
                        message.get("chat_id") or
                        message.get("sender", {}).get("user_id")
                    )
                    
                    body = message.get("body", {})
                    text = body.get("text") or message.get("text", "")
                    
                    if recipient_id and text and "http" in text:
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        process_smart_video(recipient_id, url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
