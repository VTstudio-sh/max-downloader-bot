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
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False)
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
                verify=False
            )
            print(f"Статус отправки видео: {res.status_code}")
            
    except Exception as e:
        print(f"Ошибка при обработке видео: {e}")
        send_text(chat_id, f"Произошла ошибка при скачивании: {e}")
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот запущен, проверяем связь с API...")
    
    # Сделаем тестовый запрос, чтобы проверить доступность метода updates
    try:
        test_res = requests.get(f"{BASE_URL}/updates", headers=HEADERS, verify=False, timeout=10)
        print(f"Тестовый ответ от /updates -> Код: {test_res.status_code}, Тело: {test_res.text}")
    except Exception as e:
        print(f"Ошибка тестового запроса: {e}")

    last_update_id = 0
    
    while True:
        try:
            response = requests.get(
                f"{BASE_URL}/updates", 
                headers=HEADERS, 
                params={'offset': last_update_id + 1, 'timeout': 30},
                verify=False
            )
            
            # Логируем каждый ответ, чтобы видеть, пустой он или нет
            print(f"getStatus: {response.status_code}, text: {response.text}")
            
            if response.status_code == 200:
                if response.text and response.text.strip():
                    try:
                        data = response.json()
                        updates = data if isinstance(data, list) else data.get("updates", data.get("result", []))
                        
                        for update in updates:
                            if isinstance(update, dict):
                                last_update_id = update.get("update_id", last_update_id)
                                message = update.get("message", update)
                                
                                chat_id = message.get("chat_id") or message.get("chat", {}).get("id")
                                text = message.get("text", "")
                                
                                if text and ("http://" in text or "https://" in text):
                                    words = text.split()
                                    url = next((w for w in words if w.startswith("http")), text)
                                    download_and_send(chat_id, url)
                    except Exception as json_err:
                        print(f"Ошибка разбора JSON: {json_err}")
            else:
                time.sleep(5)
                        
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
