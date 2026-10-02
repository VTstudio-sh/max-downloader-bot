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

def send_message_with_qualities(chat_id, video_url):
    """Отправляет сообщение с кнопками выбора качества через массив attachments, как требует MAX"""
    try:
        params = {"user_id": chat_id}
        
        # Правильная структура для MAX: инлайн-клавиатура внутри attachments
        data = {
            "text": f"Выберите качество:\n{video_url}",
            "attachments": [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "inline_keyboard": [
                            [
                                {"text": "1080p", "callback_data": f"1080|{video_url}"},
                                {"text": "720p", "callback_data": f"720|{video_url}"}
                            ],
                            [
                                {"text": "480p", "callback_data": f"480|{video_url}"},
                                {"text": "360p", "callback_data": f"360|{video_url}"}
                            ]
                        ]
                    }
                }
            ]
        }
        
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=data, verify=False, timeout=15)
        print(f"Ответ меню качества: статус {res.status_code}, тело: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки меню качества: {e}")

def download_and_send_video(chat_id, resolution, video_url):
    """Скачивает видео нужного качества и отправляет файл в чат"""
    filename = f"video_{chat_id}.mp4"
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        params = {"user_id": chat_id}
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json={"text": f"⚡ Скачиваю видео ({resolution}p)..."}, verify=False, timeout=15)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Видео скачано. Размер: {file_size:.2f} МБ")
            
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json={"text": f"📤 Отправляю файл ({file_size:.1f} МБ)..."}, verify=False, timeout=15)
            
            with open(filename, 'rb') as f:
                files = {'file': f}
                res = requests.post(
                    f"{BASE_URL}/messages", 
                    headers={"Authorization": TOKEN}, 
                    params=params,
                    files=files, 
                    verify=False,
                    timeout=180
                )
                print(f"Статус отправки файла: {res.status_code}, ответ: {res.text}")
                
    except Exception as e:
        print(f"Ошибка скачивания/отправки: {e}")
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params={"user_id": chat_id}, json={"text": f"❌ Ошибка при скачивании: {e}"}, verify=False, timeout=15)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("Бот с поддержкой инлайн-кнопок MAX запущен...")
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
                    # Обработка нажатий на инлайн-кнопки
                    callback = update.get("callback_query") or update.get("callback")
                    if callback:
                        chat_id = callback.get("from", {}).get("id") or callback.get("chat_id")
                        data_payload = callback.get("data", "")
                        if "|" in data_payload:
                            res_str, video_url = data_payload.split("|", 1)
                            download_and_send_video(chat_id, int(res_str), video_url)
                        continue

                    # Обработка обычного сообщения со ссылкой
                    message = update.get("message", {})
                    chat_id = (
                        message.get("chat_id") or
                        message.get("sender", {}).get("user_id") or
                        message.get("from", {}).get("id") or
                        message.get("chat", {}).get("id")
                    )
                    
                    body = message.get("body", {})
                    text = body.get("text") or message.get("text", "")
                    
                    if chat_id and text and "http" in text:
                        words = text.split()
                        url = next((w for w in words if w.startswith("http")), text)
                        send_message_with_qualities(chat_id, url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в общем цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()

