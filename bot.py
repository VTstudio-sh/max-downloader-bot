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

def send_message_with_qualities(user_id, video_url):
    """Отправляет сообщение с кнопками выбора качества через user_id для лички"""
    try:
        params = {"user_id": user_id}
        
        data = {
            "text": f"Выберите качество:\n{video_url}",
            "attachments": [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {"type": "callback", "text": "1080p", "payload": f"1080|{video_url}"},
                                {"type": "callback", "text": "720p", "payload": f"720|{video_url}"}
                            ],
                            [
                                {"type": "callback", "text": "480p", "payload": f"480|{video_url}"},
                                {"type": "callback", "text": "360p", "payload": f"360|{video_url}"}
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

def answer_callback(callback_id):
    """Гасим анимацию загрузки (часики) на кнопке через POST /answers"""
    try:
        requests.post(
            f"{BASE_URL}/answers", 
            headers=HEADERS, 
            json={"callback_id": callback_id}, 
            verify=False, 
            timeout=10
        )
    except Exception as e:
        print(f"Ошибка ответа на callback: {e}")

def download_and_send_video(target_params, resolution, video_url):
    """Скачивает видео нужного качества и отправляет файл, используя правильные параметры (user_id или chat_id)"""
    filename = f"video_temp.mp4"
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"⚡ Скачиваю видео ({resolution}p)..."}, verify=False, timeout=15)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Видео скачано. Размер: {file_size:.2f} МБ")
            
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"📤 Отправляю файл ({file_size:.1f} МБ)..."}, verify=False, timeout=15)
            
            with open(filename, 'rb') as f:
                files = {'file': f}
                res = requests.post(
                    f"{BASE_URL}/messages", 
                    headers={"Authorization": TOKEN}, 
                    params=target_params,
                    files=files, 
                    verify=False,
                    timeout=180
                )
                print(f"Статус отправки файла: {res.status_code}, ответ: {res.text}")
                
    except Exception as e:
        print(f"Ошибка скачивания/отправки: {e}")
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"❌ Ошибка при скачивании: {e}"}, verify=False, timeout=15)
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
                    event_type = update.get("type")
                    
                    # 1. Обработка нажатия на инлайн-кнопку (message_callback)
                    if event_type == "message_callback":
                        callback = update.get("callback", {})
                        callback_id = callback.get("callback_id")
                        data_payload = callback.get("payload", "")
                        message = update.get("message", {})
                        
                        # Достаем ID
                        chat_id = message.get("chat_id")
                        user_id = callback.get("user", {}).get("user_id")[span_2](start_span)[span_2](end_span)
                        
                        if callback_id:
                            answer_callback(callback_id)
                            
                        print(f"Клик по кнопке! chat_id: {chat_id}, user_id: {user_id}, payload: {data_payload}")
                        
                        # ЖЕСТКАЯ ПРОВЕРКА: если chat_id равен 0 или пустой, шлем строго через user_id[span_3](start_span)[span_3](end_span)[span_4](start_span)[span_4](end_span)
                        if chat_id is None or chat_id == 0 or chat_id == "0":
                            if user_id:
                                target_params = {"user_id": int(user_id)}
                            else:
                                continue
                        else:
                            target_params = {"chat_id": chat_id}
                        
                        if "|" in data_payload:
                            res_str, video_url = data_payload.split("|", 1)
                            download_and_send_video(target_params, int(res_str), video_url)
                        continue

                    # 2. Обработка обычного текстового сообщения
                    if event_type == "message_created" or "message" in update:
                        message = update.get("message", {})
                        user_id = (
                            message.get("sender", {}).get("user_id") or
                            message.get("from", {}).get("id")
                        )
                        
                        body = message.get("body", {})
                        text = body.get("text") or message.get("text", "")
                        
                        if user_id and text and "http" in text:
                            words = text.split()
                            url = next((w for w in words if w.startswith("http")), text)
                            send_message_with_qualities(int(user_id), url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в общем цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
