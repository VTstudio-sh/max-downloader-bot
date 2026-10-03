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
    """Отправляет сообщение с инлайн-кнопками выбора качества корректного формата MAX API"""
    try:
        params = {"user_id": user_id}
        
        # Исправлена структура вложений под стандарты MAX Bot API
        data = {
            "text": "🎬 Выберите желаемое качество для загрузки видео:",
            "attachments": [
                {
                    "type": "inline_keyboard",
                    # В MAX массивы рядов кнопок передаются прямо в список внутри rows/buttons
                    "inline_keyboard": [
                        [
                            {"type": "callback", "text": "🎬 1080p", "callback_data": f"1080|{video_url}"},
                            {"type": "callback", "text": "🎬 720p", "callback_data": f"720|{video_url}"}
                        ],
                        [
                            {"type": "callback", "text": "🎬 480p", "callback_data": f"480|{video_url}"},
                            {"type": "callback", "text": "🎬 360p", "callback_data": f"360|{video_url}"}
                        ]
                    ]
                }
            ]
        }
        
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=params, json=data, verify=False, timeout=15)
        print(f"Ответ меню качества: статус {res.status_code}, тело: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки меню качества: {e}")

def answer_callback(callback_id):
    """Уведомляет сервер MAX о получении клика, убирая анимацию загрузки на кнопке"""
    try:
        # Для гашения кнопок в MAX используется POST на /answers с callback_id
        res = requests.post(
            f"{BASE_URL}/answers", 
            headers=HEADERS, 
            json={"callback_id": callback_id}, 
            verify=False, 
            timeout=10
        )
        print(f"Ответ на callback_id {callback_id}: статус {res.status_code}")
    except Exception as e:
        print(f"Ошибка ответа на callback: {e}")

def download_and_send_video(target_params, resolution, video_url):
    """Скачивает видео нужного качества и отправляет его как полноценный видео-плеер"""
    filename = "video_temp.mp4"
    
    # yt-dlp настройки для обеспечения совместимости с плеером (mp4 h264)
    ydl_opts = {
        'format': f'bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]/best[height<={resolution}][ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_check_certificate': True,
        'merge_output_format': 'mp4'
    }
    
    try:
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"⏳ Скачиваю видео ({resolution}p)..."}, verify=False, timeout=15)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
            
        if os.path.exists(filename):
            file_size = os.path.getsize(filename) / (1024 * 1024)
            print(f"Видео скачано успешно. Размер: {file_size:.2f} МБ")
            
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"📤 Отправляю плеер с видео ({file_size:.1f} МБ)..."}, verify=False, timeout=15)
            
            # ВАЖНО: Отправляем файл с MIME-типом video/mp4, чтобы MAX отобразил кнопку PLAY
            with open(filename, 'rb') as f:
                files = {
                    'file': (filename, f, 'video/mp4')
                }
                # Убираем Content-Type из заголовков, чтобы requests сам выставил multipart/form-data
                upload_headers = {"Authorization": TOKEN}
                
                res = requests.post(
                    f"{BASE_URL}/messages", 
                    headers=upload_headers, 
                    params=target_params,
                    files=files, 
                    verify=False,
                    timeout=300
                )
                print(f"Статус отправки файла: {res.status_code}, ответ: {res.text}")
                
    except Exception as e:
        print(f"Ошибка скачивания/отправки: {e}")
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json={"text": f"❌ Ошибка при обработке видео: {e}"}, verify=False, timeout=15)
    finally:
        if os.path.exists(filename):
            os.remove(filename)

def main():
    print("🚀 Бот обработки видео MAX успешно запущен...")
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
                    
                    # 1. Обработка нажатия на инлайн-кнопку
                    if event_type == "message_callback":
                        callback = update.get("callback", {})
                        callback_id = callback.get("callback_id")
                        
                        # В MAX Bot API данные клика обычно возвращаются в callback_data или payload
                        data_payload = callback.get("callback_data") or callback.get("payload", "")
                        message = update.get("message", {})
                        
                        chat_id = message.get("chat_id")
                        user_id = callback.get("user", {}).get("user_id")
                        
                        if callback_id:
                            answer_callback(callback_id)
                            
                        print(f"Клик по кнопке! chat_id: {chat_id}, user_id: {user_id}, payload: {data_payload}")
                        
                        if chat_id is None or chat_id == 0 or chat_id == "0":
                            if user_id:
                                target_params = {"user_id": int(user_id)}
                            else:
                                continue
                        else:
                            target_params = {"chat_id": chat_id}
                        
                        if data_payload and "|" in data_payload:
                            res_str, video_url = data_payload.split("|", 1)
                            # Запуск скачивания в отдельном потоке не даст зависнуть основному циклу получения обновлений
                            import threading
                            threading.Thread(target=download_and_send_video, args=(target_params, int(res_str), video_url)).start()
                        continue

                    # 2. Обработка входящего сообщения со ссылкой
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

