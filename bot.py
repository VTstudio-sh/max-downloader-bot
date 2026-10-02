import os
import time
import requests
import urllib3
import yt_dlp
import json

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://platform-api2.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def send_text(recipient_id, text):
    try:
        # Используем chat_id в объекте recipient
        data = {
            "recipient": {
                "chat_id": str(recipient_id)
            },
            "text": text
        }
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False, timeout=15)
        print(f"Ответ сервера на текст (chat_id={recipient_id}): статус {res.status_code}, тело: {res.text}")
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
        send_text(recipient_id, "⚡ Анализирую и скачиваю видео...")
        
        with yt_dlp.YoutubeDL(ydl_opts_optimal) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Размер файла: {file_size:.2f} МБ")
            
            CHAT_LIMIT_MB = 30 
            
            if file_size <= CHAT_LIMIT_MB:
                send_text(recipient_id, f"📤 Отправляю видео в чат ({file_size:.1f} МБ)...")
                
                with open(filename, 'rb') as f:
                    files = {'file': f}
                    data = {
                        'recipient': json.dumps({"chat_id": str(recipient_id)})
                    }
                    res = requests.post(
                        f"{BASE_URL}/messages", 
                        headers={"Authorization": TOKEN}, 
                        data=data, 
                        files=files, 
                        verify=False,
                        timeout=180
                    )
                    print(f"Статус отправки файла: {res.status_code}, ответ: {res.text}")
                    if res.status_code != 200:
                        send_text(recipient_id, f"❌ Ошибка отправки файла (код {res.status_code}).")
            else:
                send_text(recipient_id, f"⚠️ Видео весит {file_size:.1f} МБ. Это больше лимита прямой отправки в чат (30 МБ).\n\n🔗 Оригинальная ссылка на видео: {video_url}")
                
    except Exception as e:
        print(f"Ошибка: {e}")
        send_text(recipient_id, f"❌ Произошла ошибка: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот запущен с исправленным chat_id в recipient...")
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

