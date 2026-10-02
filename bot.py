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

def send_text(chat_id, text, keyboard=None):
    try:
        data = {"chat_id": chat_id, "text": text}
        if keyboard:
            data["keyboard"] = keyboard
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False, timeout=15)
    except Exception as e:
        print(f"Ошибка отправки текста: {e}")

def process_video(chat_id, video_url):
    filename = f"video_{chat_id}.mp4"
    
    # Качаем в лучшем качестве, так как отправлять будем ссылкой, а не через файл в чат
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        send_text(chat_id, "⏳ Начал скачивать видео в высоком качестве, подожди пару секунд...")
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Видео скачано успешно. Размер: {file_size:.2f} МБ")
            
            # Здесь бот сообщает, что видео готово. 
            # Если у тебя настроен хостинг с публичным доктором/файлообменником, 
            # сюда можно подставить реальную ссылку на скачивание файла с сервера.
            send_text(chat_id, f"✅ Видео успешно скачано! (Вес: {file_size:.1f} МБ).\n\nПоскольку файл тяжелый, для тёти лучше всего закинуть его на Яндекс.Диск / облако или отдать прямую ссылку.")
            
    except Exception as e:
        print(f"Ошибка скачивания: {e}")
        send_text(chat_id, f"❌ Не удалось скачать видео: {e}")
    finally:
        # Удали файл после отправки, чтобы не забивать диск сервера
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот запущен и готов к работе со ссылками...")
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
                    recipient = message.get("recipient", {})
                    chat_id = recipient.get("chat_id") or message.get("chat_id")
                    
                    body = message.get("body", {})
                    text = body.get("text") or message.get("text", "")
                    
                    if chat_id and text and "http" in text:
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        process_video(chat_id, url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
