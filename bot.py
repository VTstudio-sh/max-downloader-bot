import os
import requests
import urllib3

# Отключаем предупреждения о несекурных SSL-запросах (если применимо)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

TOKEN = os.getenv("TOKEN")  # Токен берется из переменных окружения Railway
BASE_URL = "https://platform.max.ru/api/v1"  # Базовый URL платформы (замени на актуальный, если отличается)

HEADERS = {
    "Authorization": f"Bearer {TOKEN}",
    "Content-Type": "application/json"
}

def send_text(recipient_id, text):
    try:
        # Передаем идентификатор через user_id в объекте recipient
        data = {
            "recipient": {
                "user_id": str(recipient_id)
            },
            "text": text
        }
        res = requests.post(f"{BASE_URL}/messages", headers=HEADERS, json=data, verify=False, timeout=15)
        print(f"Ответ сервера на текст (recipient_id={recipient_id}): статус {res.status_code}, тело: {res.text}")
    except Exception as e:
        print(f"Ошибка отправки текста: {e}")

def main():
    print("Бот запущен и готов к работе...")
    
    # Пример структуры опроса обновлений (Long Polling / Webhook endpoint логика)
    # Здесь используется твоя базовая логика получения событий от сервера
    offset = 0
    while True:
        try:
            # Запрос обновлений (убедись, что эндпоинт получения апдейтов совпадает с документацией платформы)
            response = requests.get(f"{BASE_URL}/updates", headers=HEADERS, params={"offset": offset}, verify=False, timeout=30)
            
            if response.status_code == 200:
                updates = response.json().get("updates", [])
                for update in updates:
                    offset = update.get("update_id", offset) + 1
                    
                    message = update.get("message", {})
                    if not message:
                        continue
                        
                    # Надежно извлекаем ID пользователя или чата для ответа
                    recipient_id = (
                        message.get("sender", {}).get("user_id") or
                        message.get("chat", {}).get("chat_id") or
                        message.get("chat_id")
                    )
                    
                    text_body = message.get("text", "")
                    print(f"Получено сообщение от {recipient_id}: {text_body}")
                    
                    # Эхо-ответ или твоя бизнес-логика
                    if text_body:
                        send_text(recipient_id, f"Привет! Я получил твое сообщение: {text_body}")
                        
        except Exception as e:
            print(f"Ошибка в цикле получения обновлений: {e}")

if __name__ == "__main__":
    main()

