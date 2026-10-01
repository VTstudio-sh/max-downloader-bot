import os
import time
import requests
import urllib3
import yt_dlp

# Отключаем предупреждения о неиспользуемой SSL-проверке
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Токен бота MAX
TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://platform-api2.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def send_text(chat_id, text):
    """Отправка текстового сообщения"""
    try:
        data = {"chat_id": chat_id, "text": text}
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False, timeout=15)
        print(f"Ответ на отправку текста: {res.status_code}")
    except Exception as e:
        print(f"Ошибка отправки текста: {e}")

def download_and_send(chat_id, video_url):
    """Скачивание и отправка видеофайла"""
    filename = f"video_{chat_id}.mp4"
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': filename,
        'quiet': True,
    }
    
    try:
        send_text(chat_id, "Ссылка получена! Начинаю скачивание видео...")
        print(f"Начинаем скачивание: {video_url}")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        print("Видео скачано, отправляем файл...")
        with open(filename, 'rb') as f:
            files = {'file': f}
            data = {'chat_id': chat_id}
            res = requests.post(
                f"{BASE_URL}/messages", 
                headers={"Authorization": TOKEN}, 
                data=data, 
                files=files, 
                verify=False,
                timeout=60
            )
            print(f"Статус отправки видео: {res.status_code}")
            
    except Exception as e:
        print(f"Ошибка при обработке видео: {e}")
        send_text(chat_id, f"Произошла ошибка при скачивании: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот запущен и готов обрабатывать ссылки...")
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
                
                updates = data.get("updates", [])
                for update in updates:
                    message = update.get("message", {})
                    
                    # Точное извлечение chat_id из структуры recipient или message
                    recipient = message.get("recipient", {})
                    chat_id = recipient.get("chat_id") or message.get("chat_id")
                    
                    text = message.get("text", "")
                    
                    print(f"Распознан чат ID: {chat_id}, текст: {text}")
                    
                    if chat_id and text and ("http://" in text or "https://" in text):
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        download_and_send(chat_id, url)
            else:
                print(f"Ошибка API. Код: {response.status_code}")
                time.sleep(5)
                        
        except requests.exceptions.Timeout:
            continue
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
