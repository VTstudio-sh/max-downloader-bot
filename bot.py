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
    print("Бот запущен и настроен на работу с marker...")
    
    current_marker = None
    
    # Сначала делаем быстрый запрос, чтобы получить актуальный стартовый marker
    try:
        init_res = requests.get(f"{BASE_URL}/updates", headers=HEADERS, verify=False, timeout=10)
        if init_res.status_code == 200:
            init_data = init_res.json()
            current_marker = init_data.get("marker")
            print(f"Стартовый marker установлен: {current_marker}")
    except Exception as e:
        print(f"Не удалось получить начальный marker: {e}")

    while True:
        try:
            params = {'timeout': 30}
            if current_marker:
                params['marker'] = current_marker
                
            response = requests.get(
                f"{BASE_URL}/updates", 
                headers=HEADERS, 
                params=params,
                verify=False
            )
            
            if response.status_code == 200:
                data = response.json()
                
                # Обновляем маркер для следующего запроса, если он пришел
                if "marker" in data:
                    current_marker = data["marker"]
                
                updates = data.get("updates", [])
                if updates:
                    print(f"Получено новых апдейтов: {len(updates)}")
                    
                for update in updates:
                    # Логируем содержимое апдейта для отладки
                    print(f"Апдейт: {update}")
                    
                    message = update.get("message", update)
                    chat_id = message.get("chat_id") or message.get("chat", {}).get("id")
                    text = message.get("text", "")
                    
                    if text and ("http://" in text or "https://" in text):
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        download_and_send(chat_id, url)
            else:
                print(f"Ошибка получения апдейтов. Код: {response.status_code}, Текст: {response.text}")
                time.sleep(5)
                        
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
