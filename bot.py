import os
import time
import requests
import yt_dlp

TOKEN = os.environ.get("MAX_BOT_TOKEN")
BASE_URL = "https://platform-api.max.ru"

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def download_and_send(chat_id, video_url):
    filename = f"video_{chat_id}.mp4"
    ydl_opts = {
        'format': 'mp4/best',
        'outtmpl': filename,
        'quiet': True,
    }
    
    try:
        # 1. Скачивание видео во временный файл
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        # 2. Отправка медиафайла в чат MAX
        upload_headers = {"Authorization": f"Bearer {TOKEN}"}
        with open(filename, 'rb') as f:
            files = {'file': f}
            data = {'chat_id': chat_id}
            res = requests.post(f"{BASE_URL}/v1/messages/sendMedia", headers=upload_headers, data=data, files=files)
            print(f"Отправка видео: {res.status_code}")
            
    except Exception as e:
        print(f"Ошибка при обработке: {e}")
    finally:
        # 3. Автоматическое удаление файла после отправки
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот успешно запущен!")
    last_update_id = 0
    
    while True:
        try:
            # Лонг-полинг запрос к API MAX
            response = requests.get(
                f"{BASE_URL}/v1/updates", 
                headers=HEADERS, 
                params={'offset': last_update_id + 1, 'timeout': 30}
            )
            
            if response.status_code == 200:
                data = response.json()
                for update in data.get("updates", []):
                    last_update_id = update.get("update_id", last_update_id)
                    message = update.get("message", {})
                    chat_id = message.get("chat_id")
                    text = message.get("text", "")
                    
                    if text and text.startswith("http"):
                        download_and_send(chat_id, text)
            else:
                print(f"Ошибка API (код {response.status_code}): {response.text}")
                time.sleep(5)
                        
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
