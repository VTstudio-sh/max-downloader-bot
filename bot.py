import os
import time
import requests
import urllib3
import yt_dlp

# Отключаем предупреждения о ненадежных SSL-сертификатах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Конфигурация
TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://botapi.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def send_message_with_qualities(user_id, video_url):
    """Отправляет пользователю инлайн-кнопки с выбором качества видео"""
    try:
        params = {"user_id": user_id}
        data = {
            "text": "Выберите качество видео:",
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
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=data, verify=False, timeout=15)
    except Exception as e:
        print(f"Ошибка отправки меню качества: {e}")

def answer_callback(callback_id):
    """Подтверждает обработку нажатия инлайн-кнопки (убирает крутилку у пользователя)"""
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

def upload_video_to_max(video_path):
    """Загружает видео на сервер MAX через POST /uploads и возвращает токен файла"""
    try:
        # Шаг 1: Запрашиваем URL для загрузки файла у сервера MAX
        upload_url_res = requests.post(
            f"{BASE_URL}/uploads", 
            headers=HEADERS, 
            json={"type": "video"}, 
            verify=False, 
            timeout=15
        )
        
        if upload_url_res.status_code != 200:
            print(f"Ошибка получения URL для загрузки: {upload_url_res.text}")
            return None
            
        upload_data = upload_url_res.json()
        upload_endpoint = upload_data.get("url") or f"{BASE_URL}/uploads"
        
        # Шаг 2: Отправляем сам файл методом POST multipart/form-data
        with open(video_path, 'rb') as f:
            files = {'file': f}
            file_headers = {"Authorization": TOKEN}
            res = requests.post(
                upload_endpoint, 
                headers=file_headers, 
                files=files, 
                verify=False, 
                timeout=120
            )
            
        if res.status_code == 200:
            res_json = res.json()
            # Достаем токен файла из возможных вариантов ответа API
            token = res_json.get("token") or res_json.get("file_id") or res_json.get("payload", {}).get("token")
            return token
        else:
            print(f"Ошибка загрузки файла на сервер MAX: {res.status_code} - {res.text}")
            return None
    except Exception as e:
        print(f"Исключение при загрузке видео в MAX: {e}")
        return None

def download_and_send_video(target_params, resolution, video_url, message_id):
    """Скачивает видео через yt-dlp, загружает его на MAX и отправляет в чат в виде плеера"""
    temp_filename = f"temp_{int(time.time())}.mp4"
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': temp_filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        # Уведомляем пользователя о начале загрузки
        requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json={"text": f"⏳ Скачиваю и подготавливаю видео ({resolution}p)..."},
            verify=False,
            timeout=15
        )
        
        # Скачиваем видео во временный файл
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Видеофайл')
            
        if not os.path.exists(temp_filename):
            raise Exception("Не удалось скачать видеофайл.")
            
        print(f"Видео скачано локально: {temp_filename}. Загружаем в MAX...")
        
        # Загружаем файл на сервера MAX и получаем токен
        file_token = upload_video_to_max(temp_filename)
        
        if not file_token:
            raise Exception("Не удалось получить токен загруженного файла от сервера MAX.")
            
        # Формируем сообщение с аттачментом типа video и полученным токеном
        video_payload = {
            "text": f"🎬 {title[:100]} ({resolution}p)",
            "attachments": [
                {
                    "type": "video",
                    "payload": {
                        "token": file_token
                    }
                }
            ]
        }
        
        res = requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json=video_payload,
            verify=False,
            timeout=15
        )
        
        print(f"Ответ API на отправку видео с токеном: статус {res.status_code}, тело: {res.text}")

        # Удаляем старое сообщение с выбором качества
        if message_id:
            try:
                edit_params = target_params.copy()
                edit_params["message_id"] = message_id
                requests.delete(f"{BASE_URL}/messages", headers=HEADERS, params=edit_params, verify=False, timeout=10)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            requests.post(
                f"{BASE_URL}/messages",
                headers=HEADERS,
                params=target_params,
                json={"text": f"❌ Ошибка при обработке видео ({resolution}p): {e}"},
                verify=False,
                timeout=15
            )
        except:
            pass
            
    finally:
        # Гарантированно удаляем временный файл, чтобы не забивать диск
        if os.path.exists(temp_filename):
            try:
                os.remove(temp_filename)
            except:
                pass

def main():
    print("Бот запущен и готов к работе!")
    
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
                    event_type = update.get("type")
                    callback = update.get("callback") or update.get("message_callback", {}).get("callback")
                    
                    # Обработка нажатий на инлайн-кнопки (выбор качества)
                    if event_type == "message_callback" or callback:
                        if not callback and "callback_id" in update:
                            callback = update
                            
                        callback_id = callback.get("callback_id")
                        data_payload = callback.get("payload", "")
                        message = update.get("message", {})
                        
                        chat_id = message.get("chat_id") or update.get("chat_id")
                        user_id = callback.get("user", {}).get("user_id") or callback.get("user_id") or update.get("user_id")
                        
                        msg_id = (
                            message.get("message_id") or 
                            message.get("body", {}).get("message_id") or 
                            callback.get("message_id") or
                            update.get("message_id") or
                            update.get("message_callback", {}).get("message_id")
                        )
                        
                        if callback_id:
                            answer_callback(callback_id)
                            
                        if chat_id is None or chat_id == 0 or chat_id == "0":
                            if user_id:
                                target_params = {"user_id": int(user_id)}
                            else:
                                continue
                        else:
                            target_params = {"chat_id": chat_id}
                        
                        if "|" in data_payload:
                            res_str, video_url = data_payload.split("|", 1)
                            download_and_send_video(target_params, int(res_str), video_url, msg_id)
                        continue

                    # Обработка входящих текстовых сообщений со ссылками
                    if event_type == "message_created" or "message" in update:
                        msg = update.get("message", update)
                        user_id = (
                            msg.get("sender", {}).get("user_id") or
                            msg.get("from", {}).get("id") or
                            msg.get("user_id")
                        )
                        
                        body = msg.get("body", {})
                        text = body.get("text") or msg.get("text", "")
                        
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
