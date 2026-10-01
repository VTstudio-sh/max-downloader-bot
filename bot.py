import os
import time
import requests
import yt_dlp

# Берем токен из настроек
TOKEN = os.environ.get("MAX_BOT_TOKEN")
API_URL = f"https://api.max.ru/bot{TOKEN}"  # Укажи точный URL API платформы Макс

def download_and_send(chat_id, video_url):
    filename = f"video_{chat_id}.mp4"
    
    # Настройка скачивания видео
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': filename,
        'quiet': True,
    }
    
    try:
        # 1. Скачиваем видео во временный файл
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        # 2. Отправляем именно файл (с кнопкой Play ▶️)
        with open(filename, 'rb') as f:
            files = {'video': f}
            data = {'chat_id': chat_id}
            requests.post(f"{API_URL}/sendVideo", data=data, files=files)
            
    except Exception as e:
        print(f"Ошибка при обработке: {e}")
    finally:
        # 3. Сразу удаляем файл с сервера
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот успешно запущен!")
    last_update_id = 0
    
    # Бесконечный цикл опроса (Long Polling)
    while True:
        try:
            # Запрашиваем новые сообщения
            response = requests.get(f"{API_URL}/getUpdates", params={'offset': last_update_id + 1, 'timeout': 30})
            data = response.json()
            
            if data.get("ok"):
                for update in data.get("result", []):
                    last_update_id = update["update_id"]
                    message = update.get("message", {})
                    chat_id = message.get("chat", {}).get("id")
                    text = message.get("text", "")
                    
                    if text.startswith("http"):
                        download_and_send(chat_id, text)
                        
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
