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
    try:
        res = requests.delete(f"{BASE_URL}/subscriptions", headers=HEADERS, verify=False, timeout=10)
        print(f"Сброс старого вебхука: статус {res.status_code}, ответ: {res.text}")
    except Exception as e:
        print(f"Не удалось сбросить вебхук: {e}")

def delete_message(target_params, message_id):
    """Удаляет сообщение по его ID"""
    if not message_id:
        return
    try:
        delete_params = target_params.copy()
        delete_params["message_id"] = message_id
        requests.delete(f"{BASE_URL}/messages", headers=HEADERS, params=delete_params, verify=False, timeout=10)
    except Exception as e:
        print(f"Ошибка удаления сообщения: {e}")

def send_message_with_qualities(user_id, video_url):
    try:
        params = {"user_id": user_id}
        
        # Сначала отправим сообщение без кнопок, чтобы узнать его message_id, 
        # либо сформируем временное меню, но проще сделать отправку и сразу забрать message_id из ответа сервера.
        initial_data = {
            "text": "⏳ Подготовка меню качества..."
        }
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=initial_data, verify=False, timeout=15)
        
        msg_id = None
        try:
            res_json = res.json()
            msg_id = res_json.get("message_id") or res_json.get("body", {}).get("message_id")
        except:
            pass
            
        if not msg_id:
            # Если поймать ID не удалось, шлем обычным способом
            return

        # Теперь редактируем это сообщение, добавляя в него клавиатуру и текст, 
        # либо отправляем новые кнопки сшитые с этим msg_id. 
        # Самый надежный способ: удалить временное и отправить нормальное с кнопками, зашившими его ID.
        delete_message(params, msg_id)

        data = {
            "text": "Выберите качество видео:",
            "attachments": [
                {
                    "type": "inline_keyboard",
                    "payload": {
                        "buttons": [
                            [
                                {"type": "callback", "text": "1080p", "payload": f"1080|{msg_id}|{video_url}"},
                                {"type": "callback", "text": "720p", "payload": f"720|{msg_id}|{video_url}"}
                            ],
                            [
                                {"type": "callback", "text": "480p", "payload": f"480|{msg_id}|{video_url}"},
                                {"type": "callback", "text": "360p", "payload": f"360|{msg_id}|{video_url}"}
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

def process_video_request(target_params, resolution, video_url, message_id_to_delete):
    # Удаляем сообщение с выбором качества по переданному через payload ID
    if message_id_to_delete:
        delete_message(target_params, message_id_to_delete)
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(video_url, download=False)
            direct_url = info_dict.get('url')
            title = info_dict.get('title', 'Видео')
            
        if direct_url:
            print(f"Прямая ссылка получена: {direct_url[:60]}...")
            
            result_data = {
                "text": f"🎬 {title} ({resolution}p)\n{direct_url}"
            }
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json=result_data, verify=False, timeout=15)
        else:
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": "❌ Не удалось получить прямую ссылку на видео."}, verify=False, timeout=15)
                
    except Exception as e:
        print(f"Ошибка обработки: {e}")
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"❌ Ошибка: {e}"}, verify=False, timeout=15)

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
                        
                        # Парсим payload формата: качество | id_сообщения | ссылка
                        parts = data_payload.split("|")
                        if len(parts) >= 3:
                            res_str = parts[0]
                            msg_to_delete_id = int(parts[1])
                            video_url = parts[2]
                            process_video_request(target_params, int(res_str), video_url, msg_to_delete_id)
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
