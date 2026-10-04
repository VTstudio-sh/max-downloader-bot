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

def download_and_send_video(target_params, resolution, video_url, message_id):
    # Настройки yt-dlp для быстрого извлечения ссылок без скачивания на диск[span_1](start_span)[span_1](end_span)
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        # Информируем пользователя о начале генерации плеера[span_2](start_span)[span_2](end_span)
        requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json={"text": f"⚙️ Генерирую плеер для качества {resolution}p..."},
            verify=False,
            timeout=15
        )
        
        # Быстро забираем метаданные и прямую ссылку у VK без загрузки видео на диск[span_3](start_span)[span_3](end_span)
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=False)
            direct_video_url = info.get('url')
            title = info.get('title', 'Видеофайл')
            thumbnail_url = info.get('thumbnail', '')
            duration = info.get('duration', 0)
            
        if not direct_video_url:
            raise Exception("Не удалось получить прямую ссылку на видеопоток.")
            
        # Формируем специальный JSON для API MAX, чтобы появился плеер с кнопкой Play[span_4](start_span)[span_4](end_span)
        video_payload = {
            "text": f"🎬 {title} ({resolution}p)",
            "attachments": [
                {
                    "type": "video",  # Указываем тип вложения как видео[span_5](start_span)[span_5](end_span)
                    "payload": {
                        "url": direct_video_url,  # Прямая ссылка на поток (ваша длинная ссылка из okcdn)[span_6](start_span)[span_6](end_span)
                        "title": title,  # Заголовок видео[span_7](start_span)[span_7](end_span)
                        "image_url": thumbnail_url,  # Обложка, которая покажется до нажатия Play[span_8](start_span)[span_8](end_span)
                        "duration": int(duration) if duration else 0  # Длительность в секундах[span_9](start_span)[span_9](end_span)
                    }
                }
            ]
        }
        
        # Отправляем видео-аттачмент в MAX[span_10](start_span)[span_10](end_span)
        res = requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json=video_payload,
            verify=False,
            timeout=15
        )
        print(f"<- Статус отправки видео-плеера: {res.status_code}, ответ: {res.text}")
        
        # Удаляем сообщение с кнопками качества, если есть его ID
        if message_id:
            try:
                edit_params = target_params.copy()
                edit_params["message_id"] = message_id
                requests.delete(f"{BASE_URL}/messages", headers=HEADERS, params=edit_params, verify=False, timeout=10)
            except:
                pass
                
    except Exception as e:
        print(f"❌ Ошибка извлечения/отправки видео: {e}")
        try:
            requests.post(
                f"{BASE_URL}/messages",
                headers=HEADERS,
                params=target_params,
                json={"text": f"❌ Ошибка в качестве {resolution}p. Ошибка: {e}"},
                verify=False,
                timeout=15
            )
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
