import os
import time
import requests
import urllib3
import yt_dlp

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://botapi.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def reset_webhook_on_start():
    """Принудительно очищаем старый вебхук, чтобы работал Long Polling"""
    try:
        res = requests.delete(f"{BASE_URL}/subscriptions", headers=HEADERS, verify=False, timeout=10)
        print(f"Сброс старого вебхука: статус {res.status_code}, ответ: {res.text}")
    except Exception as e:
        print(f"Не удалось сбросить вебхук (возможно, уже пуст): {e}")

def send_message_with_qualities(user_id, video_url):
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
    filename = "video_temp.mp4"
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
    print("Бот запущен, сбрасываем старые подписки...")
    reset_webhook_on_start()
    
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
                    # Выводим вообще весь апдейт в лог, чтобы увидеть, что именно приходит при клике
                    print(f"Получен апдейт: {update}")
                    
                    event_type = update.get("type")
                    
                    # Ловим callback в разных вариациях структуры
                    callback = update.get("callback") or update.get("message_callback", {}).get("callback")
                    
                    if event_type == "message_callback" or callback:
                        if not callback and "callback_id" in update:
                            callback = update
                            
                        callback_id = callback.get("callback_id")
                        data_payload = callback.get("payload", "")
                        message = update.get("message", {})
                        
                        chat_id = message.get("chat_id")
                        user_id = callback.get("user", {}).get("user_id") or callback.get("user_id")
                        
                        if callback_id:
                            answer_callback(callback_id)
                            
                        print(f"Клик! chat_id: {chat_id}, user_id: {user_id}, payload: {data_payload}")
                        
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

                    # Обработка текстовых сообщений
                    if event_type == "message_created" or "message" in update:
                        message = update.get("message", update)
                        user_id = (
                            message.get("sender", {}).get("user_id") or
                            message.get("from", {}).get("id") or
                            message.get("user_id")
                        )
                        
                        body = message.get("body", {})
                        text = body.get("text") or message.get("text", "")
                        
                        if user_id and text and "http" in text:
                            words = text.split()
                            url = next((w for w in words if w.startswith("http")), text)
                            send_message_with_qualities(int(user_id), url)
            else:
                print(f"Ошибка получения обновлений: статус {response.status_code}, текст: {response.text}")
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в общем цикле: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
