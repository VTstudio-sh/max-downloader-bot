import os
import time
import json
import requests
import urllib3
import yt_dlp
import threading
import sqlite3
import hashlib

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = "f9LHodD0cOKUGzWblFvIN7u9vshHsp6jWb8TCzfs1wUyXA5CRWycHvLc03Lm9Twzj24NqrDCe1DXTR-2u7hd"
BASE_URL = "https://botapi.max.ru"

HEADERS = {
    "Authorization": TOKEN,
    "Content-Type": "application/json"
}

STATE_FILE = "state.json"
DB_FILE = "bot_history.db"
download_locks = {}
lock_mutex = threading.Lock()

# --- ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ---
def init_db():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    # Таблица для хранения хэшей обработанных сообщений
    cursor.execute('''CREATE TABLE IF NOT EXISTS processed_events
                      (event_hash TEXT PRIMARY KEY, timestamp REAL)''')
    conn.commit()
    conn.close()

def is_event_processed(event_hash):
    """Проверяет, было ли событие раньше, и записывает его, если нет"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    try:
        # Пытаемся вставить хэш. Если он уже есть (PRIMARY KEY), SQLite выдаст ошибку IntegrityError
        cursor.execute("INSERT INTO processed_events (event_hash, timestamp) VALUES (?, ?)", (event_hash, time.time()))
        conn.commit()
        return False # Событие новое
    except sqlite3.IntegrityError:
        return True # Событие уже было в базе
    finally:
        conn.close()

def cleanup_db():
    """Удаляет старые записи из базы, чтобы она не росла бесконечно (оставляем за последние 24 часа)"""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM processed_events WHERE timestamp < ?", (time.time() - 86400,))
    conn.commit()
    conn.close()
# ---------------------------------

def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, 'r') as f:
                return json.load(f)
        except: pass
    return {"marker": None}

def save_state(marker):
    try:
        with open(STATE_FILE, 'w') as f:
            json.dump({"marker": marker}, f)
    except Exception as e:
        print(f"Ошибка сохранения: {e}")

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
        print(f"Ошибка отправки меню: {e}")

def answer_callback(callback_id):
    try:
        requests.post(f"{BASE_URL}/answers", headers=HEADERS, json={"callback_id": callback_id}, verify=False, timeout=10)
    except Exception as e:
        print(f"Ошибка ответа на callback: {e}")

def upload_video_to_max(video_path):
    try:
        step1_url = "https://platform-api2.max.ru/uploads"
        params = {"type": "video"}
        step1_headers = {"Accept": "application/json", "Authorization": TOKEN}
        
        print(f"Шаг 1: Запрос ссылки и токена...")
        res1 = requests.post(step1_url, params=params, headers=step1_headers, verify=False, timeout=15)
        if res1.status_code != 200: return None
            
        data1 = res1.json()
        upload_url = data1.get("url")
        file_token = data1.get("token")
        if not upload_url: return None
            
        print(f"Шаг 2: Загрузка файла...")
        with open(video_path, 'rb') as f:
            files = {'file': (os.path.basename(video_path), f, 'video/mp4')}
            res2 = requests.post(upload_url, files=files, verify=False, timeout=180)
            
        if res2.status_code != 200:
            with open(video_path, 'rb') as f:
                files = {'data': f}
                res2 = requests.post(upload_url, files=files, verify=False, timeout=180)
            
        return file_token if res2.status_code == 200 else None
    except Exception as e:
        print(f"Исключение при загрузке: {e}")
        return None

def download_and_send_video(target_params, resolution, video_url, message_id, user_id):
    lock_key = f"{user_id}_{resolution}"
    with lock_mutex:
        if lock_key in download_locks and download_locks[lock_key].is_alive():
            print(f"Видео уже качается. Игнорируем.")
            return
        download_locks[lock_key] = threading.Event()

    temp_filename = f"temp_{int(time.time())}_{resolution}.mp4"
    ydl_opts = {
        'format': f'best[height<={resolution}][ext=mp4]/best[ext=mp4]/best',
        'outtmpl': temp_filename, 'quiet': True, 'no_check_certificate': True,
        'socket_timeout': 30, 'geo_bypass': True,
    }
    
    try:
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params,
            json={"text": f"⏳ Скачиваю и подготавливаю видео ({resolution}p)..."}, verify=False, timeout=15)
        
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(video_url, download=True)
            title = info.get('title', 'Видеофайл')
            
        if not os.path.exists(temp_filename) or os.path.getsize(temp_filename) == 0:
            raise Exception("Файл пустой.")
            
        print(f"Видео скачано. Загружаем в MAX...")
        file_token = upload_video_to_max(temp_filename)
        if not file_token: raise Exception("Не удалось получить токен файла.")
            
        video_payload = {
            "text": f"🎬 {title[:100]} ({resolution}p)",
            "attachments": [{"type": "video", "payload": {"token": file_token}}]
        }
        
        requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params, json=video_payload, verify=False, timeout=15)

        if message_id:
            try:
                edit_params = target_params.copy()
                edit_params["message_id"] = message_id
                requests.delete(f"{BASE_URL}/messages", headers=HEADERS, params=edit_params, verify=False, timeout=10)
            except: pass
                
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            requests.post(f"{BASE_URL}/messages", headers=HEADERS, params=target_params,
                json={"text": f"❌ Ошибка при обработке видео ({resolution}p): {e}"}, verify=False, timeout=15)
        except: pass
    finally:
        if os.path.exists(temp_filename):
            try: os.remove(temp_filename)
            except: pass
        with lock_mutex:
            if lock_key in download_locks: del download_locks[lock_key]

def main():
    print("Бот запущен! Используется база данных SQLite для 100% защиты от дублей.")
    init_db()
    cleanup_db() # Чистим старье при старте
    
    state = load_state()
    current_marker = state.get("marker")
    last_cleanup = time.time()
    
    while True:
        try:
            # Раз в час чистим старые записи из базы
            if time.time() - last_cleanup > 3600:
                cleanup_db()
                last_cleanup = time.time()

            params = {'timeout': 30}
            if current_marker: params['marker'] = current_marker
                
            response = requests.get(f"{BASE_URL}/updates", headers=HEADERS, params=params, verify=False, timeout=45)
            
            if response.status_code == 200:
                data = response.json()
                new_marker = data.get("marker")
                updates = data.get("updates", [])
                
                for update in updates:
                    event_type = update.get("type")
                    callback = update.get("callback") or update.get("message_callback", {}).get("callback")
                    
                    # === КНОПКИ ===
                    if event_type == "message_callback" or callback:
                        if not callback and "callback_id" in update:
                            callback = update
                            
                        callback_id = callback.get("callback_id")
                        data_payload = callback.get("payload", "")
                        message = update.get("message", {})
                        
                        chat_id = message.get("chat_id") or update.get("chat_id")
                        user_id = callback.get("user", {}).get("user_id") or callback.get("user_id") or update.get("user_id")
                        
                        # Создаем хэш нажатия кнопки (юзер + данные кнопки)
                        event_hash = hashlib.md5(f"cb_{user_id}_{data_payload}".encode()).hexdigest()
                        
                        if is_event_processed(event_hash):
                            print(f"Дубль кнопки от {user_id} заблокирован БД.")
                            if callback_id: answer_callback(callback_id)
                            continue
                            
                        if callback_id: answer_callback(callback_id)
                        
                        msg_id = (message.get("message_id") or message.get("body", {}).get("message_id") or 
                                  callback.get("message_id") or update.get("message_id") or 
                                  update.get("message_callback", {}).get("message_id"))
                        
                        if chat_id is None or chat_id == 0 or chat_id == "0":
                            if user_id: target_params = {"user_id": int(user_id)}
                            else: continue
                        else: target_params = {"chat_id": chat_id}
                        
                        if "|" in data_payload:
                            res_str, video_url = data_payload.split("|", 1)
                            threading.Thread(target=download_and_send_video, 
                                args=(target_params, int(res_str), video_url, msg_id, user_id)).start()
                        continue

                    # === ТЕКСТ ===
                    if event_type == "message_created" or "message" in update:
                        msg = update.get("message", update)
                        body = msg.get("body", {})
                        user_id = (msg.get("sender", {}).get("user_id") or msg.get("from", {}).get("id") or msg.get("user_id"))
                        text = body.get("text") or msg.get("text", "")
                        
                        if user_id and text and "http" in text:
                            # Создаем хэш текста (юзер + текст)
                            event_hash = hashlib.md5(f"msg_{user_id}_{text}".encode()).hexdigest()
                            
                            if is_event_processed(event_hash):
                                print(f"Дубль сообщения от {user_id} заблокирован БД.")
                                continue
                                
                            words = text.split()
                            url = next((w for w in words if w.startswith("http")), text)
                            send_message_with_qualities(int(user_id), url)

                if new_marker:
                    current_marker = new_marker
                    save_state(current_marker)
            else:
                time.sleep(3)
        except Exception as e:
            print(f"Ошибка в общем цикле: {e}")
            time.sleep(3)

if __name__ == '__main__':
    main()
