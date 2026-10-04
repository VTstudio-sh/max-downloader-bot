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

def send_message_with_qualities(user_id, video_url):
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
    """Двухэтапная загрузка видео по официальной документации МАХ"""
    try:
        # Шаг 1: Получаем персональную URL-ссылку для загрузки файла
        step1_url = "https://platform-api2.max.ru/uploads"
        params = {"type": "video"}
        step1_headers = {
            "Accept": "application/json",
            "Authorization": TOKEN
        }
        
        print(f"Шаг 1: Запрос ссылки для загрузки видео...")
        res1 = requests.post(step1_url, params=params, headers=step1_headers, verify=False, timeout=15)
        print(f"Ответ Шага 1 (статус {res1.status_code}): {res1.text}")
        
        if res1.status_code != 200:
            return None
            
        data1 = res1.json()
        upload_url = data1.get("url")
        
        if not upload_url:
            print(f"Не найдена ссылка 'url' в ответе: {data1}")
            return None
            
        # Шаг 2: Отправляем сам файл на полученный URL методом POST (multipart/form-data)
        print(f"Шаг 2: Загрузка файла на полученный URL...")
        with open(video_path, 'rb') as f:
            files = {'data': f}
            res2 = requests.post(upload_url, files=files, headers={"Authorization": TOKEN}, verify=False, timeout=180)
            
        print(f"Ответ Шага 2 (статус {res2.status_code}): {res2.text}")
            
        if res2.status_code == 200:
            res2_json = res2.json()
            
            # Универсальный поиск токена в ответе сервера
            token = (
                res2_json.get("token") or 
                res2_json.get("file_id") or 
                res2_json.get("payload", {}).get("token") or
                res2_json.get("data", {}).get("token")
            )
            
            # Глубокий поиск, если структура вложена (например, в словари типа photos/videos)
            if not token:
                for key, val in res2_json.items():
                    if isinstance(val, dict):
                        for sub_k, sub_v in val.items():
                            if isinstance(sub_v, dict) and "token" in sub_v:
                                token = sub_v["token"]
                                break
                            elif sub_k == "token":
                                token = sub_v
                                break
                    if token:
                        break
                        
            return token
        else:
            print(f"Ошибка при загрузке файла на URL: {res2.status_code} - {res2.text}")
            return None
    except Exception as e:
        print(f"Исключение при двухэтапной загрузке видео в MAX: {e}")
        return None

def download_and_send_video(target_params, resolution, video_url, message_id):
    temp_filename = f"temp_{int(time.time())}.mp4"
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': temp_filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json={"text": f"⏳ Скачиваю и подготавливаю видео ({resolution}p)..."},
            verify=False,
            timeout=15
        )
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Видеофайл')
            
        if not os.path.exists(temp_filename):
            raise Exception("Не удалось скачать видеофайл.")
            
        print(f"Видео скачано локально: {temp_filename}. Загружаем в MAX...")
        
        file_token = upload_video_to_max(temp_filename)
        
        if not file_token:
            raise Exception("Не удалось получить токен загруженного файла от сервера MAX.")
            
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
