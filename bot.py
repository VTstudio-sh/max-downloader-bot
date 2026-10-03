import os
import time
import requests
import urllib3
import yt_dlp

# Отключаем предупреждения об отсутствии SSL-сертификатов для стабильной работы на хостингах
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

def send_message_with_qualities(user_id, video_url):
    """Отправляет инлайн-кнопки выбора качества в личный чат"""
    try:
        print(f"-> Отправляю меню качества для пользователя {user_id}...")
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
        print(f"<- Ответ меню качества: статус {res.status_code}, тело: {res.text}")
    except Exception as e:
        print(f"❌ Ошибка отправки меню качества: {e}")

def answer_callback(callback_id):
    """Убирает индикатор загрузки ('часики') на инлайн-кнопке"""
    try:
        print(f"-> Гашу callback_id: {callback_id}")
        # В API MAX параметр callback_id передается строго в строке запроса (params)
        res = requests.post(
            f"{BASE_URL}/answers", 
            headers=HEADERS, 
            params={"callback_id": callback_id}, 
            json={}, 
            verify=False, 
            timeout=10
        )
        print(f"<- Ответ на callback: статус {res.status_code}")
    except Exception as e:
        print(f"❌ Ошибка ответа на callback: {e}")

def download_and_send_video(target_params, resolution, video_url):
    """Скачивает видео нужного качества и отправляет его как файл"""
    filename = "video_temp.mp4"
    
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
    }
    
    try:
        print(f"-> Отправляю статус скачивания пользователю...")
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"⚡ Скачиваю видео ({resolution}p)..."}, verify=False, timeout=15)
        
        print(f"-> Запуск скачивания через yt-dlp: {video_url} в {resolution}p")
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"✅ Видео успешно скачано. Размер файла: {file_size:.2f} МБ")
            
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"📤 Отправляю файл ({file_size:.1f} МБ)..."}, verify=False, timeout=15)
            
            print(f"-> Отправка бинарного файла в MAX API...")
            with open(filename, 'rb') as f:
                # Content-Type не указываем, requests соберет multipart/form-data автоматически
                file_headers = {"Authorization": TOKEN}
                files = {
                    'file': (filename, f, 'video/mp4')
                }
                
                res = requests.post(
                    f"{BASE_URL}/messages", 
                    headers=file_headers, 
                    params=target_params,
                    files=files, 
                    verify=False,
                    timeout=300
                )
                print(f"<- Статус отправки файла: {res.status_code}, ответ сервера: {res.text}")
        else:
            print("❌ Файл не был найден после скачивания.")
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"❌ Ошибка: Не удалось сохранить видео файл."}, verify=False, timeout=15)
                
    except Exception as e:
        print(f"❌ Ошибка в процессе скачивания или отправки: {e}")
        try:
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"❌ Произошла ошибка: {e}"}, verify=False, timeout=15)
        except:
            pass
    finally:
        if os.path.exists(filename):
            print(f"-> Удаляю временный файл {filename}")
            os.remove(filename)

def main():
    print("==================================================")
    print("Бот с поддержкой инлайн-кнопок MAX запущен...")
    print("==================================================")
    
    # Сбрасываем вебхуки, чтобы сервер принудительно перенаправил сообщения в Long Polling
    try:
        print("-> Сбрасываю старые Webhook настройки на сервере MAX...")
        res = requests.post(f"{BASE_URL}/webhooks/set", headers=HEADERS, json={"url": ""}, verify=False, timeout=10)
        print(f"<- Статус сброса вебхука: {res.status_code}. Теперь Long Polling активен.")
    except Exception as e:
        print(f"⚠️ Предупреждение при сбросе вебхука: {e}")

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
            
            if response.status_code != 200:
                print(f"⚠️ Ошибка Long Polling. Статус: {response.status_code}, Ответ: {response.text}")
                time.sleep(5)
                continue
                
            data = response.json()
            if "marker" in data:
                current_marker = data["marker"]
            
            updates = data.get("updates", [])
            if updates:
                print(f"--- Получено новых событий от сервера: {len(updates)} ---")
            
            for update in updates:
                event_type = update.get("type")
                print(f"🏷️ Обнаружено событие: {event_type}")
                
                # 1. ОБРАБОТКА НАЖАТИЯ НА ИНЛАЙН-КНОПКУ
                if event_type == "message_callback":
                    callback = update.get("callback", {})
                    callback_id = callback.get("callback_id")
                    data_payload = callback.get("payload", "")
                    message = update.get("message", {})
                    
                    chat_id = message.get("chat_id", 0)
                    user_id = callback.get("user", {}).get("user_id")
                    
                    print(f"🔘 Нажата кнопка! chat_id={chat_id}, user_id={user_id}, payload={data_payload}")
                    
                    if callback_id:
                        answer_callback(callback_id)
                        
                    # Если личный чат (chat_id равен 0 или отсутствует)
                    if chat_id is None or chat_id == 0 or chat_id == "0":
                        if user_id:
                            target_params = {"user_id": int(user_id)}
                        else:
                            print("⚠️ В callback событии отсутствует user_id!")
                            continue
                    else:
                        # Если это групповой чат
                        target_params = {"chat_id": chat_id}
                    
                    if "|" in data_payload:
                        res_str, video_url = data_payload.split("|", 1)
                        download_and_send_video(target_params, int(res_str), video_url)
                    continue

                # 2. ОБРАБОТКА ОБЫЧНОГО ТЕКСТОВОГО СООБЩЕНИЯ
                if event_type == "message_created":
                    message = update.get("message", {})
                    user_id = message.get("sender", {}).get("user_id")
                    text = message.get("text", "")
                    
                    print(f"📩 Текст от пользователя {user_id}: {text}")
                    
                    if user_id and text and "http" in text:
                        words = text.split()
                        # Извлекаем первую попавшуюся ссылку из сообщения
                        url = next((w for w in words if w.startswith("http")), text)
                        send_message_with_qualities(int(user_id), url)
                            
        except Exception as e:
            print(f"❌ Критическая ошибка в цикле Long Polling: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
