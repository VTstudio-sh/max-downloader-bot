import os
import re
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

# Защита от дублей — храним обработанные ID событий
processed_updates = set()
processed_message_ids = set()
processed_callbacks = set()


def clean_url(url):
    """Приводим ссылки YouTube/VK/TikTok к правильному виду."""
    url = url.strip().rstrip('.,;!?)')

    if "youtu.be/" in url:
        vid = url.split("youtu.be/")[1].split("?")[0].split("&")[0]
        return f"https://www.youtube.com/watch?v={vid}"

    if "youtube.com/shorts/" in url:
        vid = url.split("youtube.com/shorts/")[1].split("?")[0].split("&")[0].split("/")[0]
        return f"https://www.youtube.com/watch?v={vid}"

    if "youtube.com/watch" in url:
        m = re.search(r"[?&]v=([a-zA-Z0-9_-]+)", url)
        if m:
            return f"https://www.youtube.com/watch?v={m.group(1)}"

    if "vk.com/" in url or "vkvideo.ru/" in url:
        return url.split("?")[0]

    if "tiktok.com/" in url:
        return url.split("?")[0]

    return url


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
    try:
        step1_url = "https://platform-api2.max.ru/uploads"
        params = {"type": "video"}
        step1_headers = {
            "Accept": "application/json",
            "Authorization": TOKEN
        }

        res1 = requests.post(step1_url, params=params, headers=step1_headers, verify=False, timeout=15)
        if res1.status_code != 200:
            print(f"Ошибка получения upload URL: {res1.status_code} — {res1.text}")
            return None

        data1 = res1.json()
        upload_url = data1.get("url")
        file_token = data1.get("token")

        if not upload_url:
            return None

        with open(video_path, 'rb') as f:
            files = {'data': (os.path.basename(video_path), f, 'video/mp4')}
            res2 = requests.post(upload_url, files=files, verify=False, timeout=180)

        if res2.status_code != 200:
            with open(video_path, 'rb') as f:
                files = {'file': f}
                res2 = requests.post(upload_url, files=files, verify=False, timeout=180)

        if res2.status_code == 200:
            try:
                resp_data = res2.json()
                return resp_data.get("token") or file_token
            except:
                return file_token
        else:
            print(f"Ошибка загрузки: {res2.status_code} — {res2.text}")
            return None
    except Exception as e:
        print(f"Ошибка загрузки в MAX: {e}")
        return None


def download_via_ytdlp(video_url, resolution, output_path):
    """Скачивание через yt-dlp (работает и для YouTube, и для VK)."""
    clean = clean_url(video_url)
    print(f"[yt-dlp] Оригинал: {video_url}")
    print(f"[yt-dlp] Очищенная: {clean}")

    fmt = (
        f"bestvideo[height<={resolution}][ext=mp4]+bestaudio[ext=m4a]"
        f"/best[height<={resolution}][ext=mp4]"
        f"/best[height<={resolution}]/best"
    )

    ydl_opts = {
        'format': fmt,
        'outtmpl': output_path,
        'merge_output_format': 'mp4',
        'quiet': False,
        'no_warnings': False,
        'nocheckcertificate': True,
        'geo_bypass': True,
        'noprogress': True,
        'http_headers': {
            'User-Agent': (
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/120.0.0.0 Safari/537.36'
            )
        }
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean])
        if os.path.exists(output_path):
            return output_path
    except Exception as e:
        print(f"[yt-dlp] Ошибка: {e}")

    return None


def send_video_to_max_with_retry(target_params, resolution, file_token):
    """Пробуем отправить видео до 6 раз, если MAX ещё не обработал файл."""
    video_payload = {
        "text": f"🎬 Готово! ({resolution}p)",
        "attachments": [
            {"type": "video", "payload": {"token": file_token}}
        ]
    }

    for attempt in range(6):
        res = requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json=video_payload,
            verify=False,
            timeout=15
        )
        print(f"Попытка {attempt + 1}: {res.status_code} — {res.text[:200]}")

        if res.status_code == 200:
            return True

        # Если MAX ещё не обработал видео — ждём и пробуем снова
        if "attachment.not.ready" in res.text or "not_processed" in res.text:
            time.sleep(5)
            continue
        else:
            return False

    return False


def download_and_send_video(target_params, resolution, video_url, message_id):
    temp_filename = f"temp_{int(time.time())}.mp4"

    try:
        requests.post(
            f"{BASE_URL}/messages",
            headers=HEADERS,
            params=target_params,
            json={"text": f"⏳ Скачиваю видео ({resolution}p)..."},
            verify=False,
            timeout=15
        )

        result_path = download_via_ytdlp(video_url, resolution, temp_filename)
        if not result_path:
            raise Exception("Не удалось скачать видео.")

        if not os.path.exists(temp_filename) or os.path.getsize(temp_filename) == 0:
            raise Exception("Файл пустой.")

        print(f"Видео скачано ({os.path.getsize(temp_filename)} байт), загружаю в MAX...")
        file_token = upload_video_to_max(temp_filename)
        if not file_token:
            raise Exception("Не удалось получить токен от MAX.")

        # Ждём, чтобы MAX обработал видео
        print("Ждём 10 секунд, пока MAX обработает видео...")
        time.sleep(10)

        # Пытаемся отправить с повторами
        success = send_video_to_max_with_retry(target_params, resolution, file_token)
        if not success:
            raise Exception("MAX не смог обработать видео.")

    except Exception as e:
        print(f"❌ Ошибка: {e}")
        try:
            requests.post(
                f"{BASE_URL}/messages",
                headers=HEADERS,
                params=target_params,
                json={"text": f"❌ Ошибка: {e}"},
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
    print("Бот для MAX запущен!")
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
                    # ===== ЗАЩИТА ОТ ДУБЛЕЙ =====
                    # 1. Проверяем ID апдейта
                    update_id = update.get("update_id") or update.get("id")
                    if update_id and update_id in processed_updates:
                        continue
                    if update_id:
                        processed_updates.add(update_id)
                        if len(processed_updates) > 1000:
                            processed_updates.clear()

                    event_type = update.get("type")
                    callback = update.get("callback") or update.get("message_callback", {}).get("callback")

                    if event_type == "message_callback" or callback:
                        if not callback and "callback_id" in update:
                            callback = update

                        callback_id = callback.get("callback_id")

                        # Защита от дублей колбэков
                        if callback_id and callback_id in processed_callbacks:
                            print(f"Дубль колбэка {callback_id} пропущен")
                            continue
                        if callback_id:
                            processed_callbacks.add(callback_id)
                            if len(processed_callbacks) > 1000:
                                processed_callbacks.clear()

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

                        # Защита от дублей сообщений — по mid
                        body = msg.get("body", {})
                        mid = body.get("mid") or msg.get("message_id") or msg.get("id")

                        if mid and mid in processed_message_ids:
                            print(f"Дубль сообщения {mid} пропущен")
                            continue
                        if mid:
                            processed_message_ids.add(mid)
                            if len(processed_message_ids) > 1000:
                                processed_message_ids.clear()

                        user_id = (
                            msg.get("sender", {}).get("user_id") or
                            msg.get("from", {}).get("id") or
                            msg.get("user_id")
                        )
                        text = body.get("text") or msg.get("text", "")

                        if user_id and text and "http" in text:
                            words = text.split()
                            url = next((w for w in words if w.startswith("http")), text)
                            url = clean_url(url)
                            send_message_with_qualities(int(user_id), url)
            else:
                time.sleep(5)
        except Exception as e:
            print(f"Ошибка в цикле обновлений: {e}")
            time.sleep(5)


if __name__ == '__main__':
    main()
