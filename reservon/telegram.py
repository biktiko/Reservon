import requests
import logging

logger = logging.getLogger(__name__)

INTERCONNECT_API_URL = "https://reservon.am/api/json.php"  # Подставьте реальный URL
INTERCONNECT_API_KEY = "38e47e13-2733-4925-96ee-59752b05d152"

def send_telegram_via_interconnect(phone_number: str, message: str, msg_id: int = 1) -> bool:
    """
    Отправляет сообщение через сервис InterConnect Solutions по Telegram.
    phone_number: строка с номером вида '380971234567' (без '+', если того требует API).
    message: строка, которую отправляем.
    msg_id: ваш уникальный ID для запроса (просто число).
    Возвращает True/False — успех или нет.
    """
    payload = {
        "auth": INTERCONNECT_API_KEY,
        "data": [
            {
                "type": "telegram",
                "id": msg_id,
                "phone": phone_number,
                "message": message,
                "telegram_lifetime": 172800,   # 2 дня
                # "hook": "https://example.org/webhook/url.php",  # если нужно
            }
        ]
    }

    headers = {
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(INTERCONNECT_API_URL, json=payload, headers=headers, timeout=10)
        response_data = response.json()
        if response.ok and response_data.get("success") is True:
            logger.info(f"Telegram message to {phone_number} sent OK: {response_data}")
            return True
        else:
            logger.error(f"Telegram message to {phone_number} failed: {response_data}")
            return False
    except Exception as e:
        logger.exception(f"Ошибка при запросе в InterConnect: {e}")
        return False
