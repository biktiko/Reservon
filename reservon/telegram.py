# # C:\Reservon\Reservon\reservon\telegram.py
# import requests
# import logging

# logger = logging.getLogger(__name__)

# INTERCONNECT_API_URL = "https://portal.interconnect.solutions/api/json.php"
# INTERCONNECT_API_KEY = "38e47e13-2733-4925-96ee-59752b05d152"

# def send_telegram_via_interconnect(phone_number: str, message: str, msg_id: int = 1) -> bool:

#     payload = {
#         "auth": INTERCONNECT_API_KEY,
#         "data": [
#             {
#                 "type": "telegram",
#                 "id": 100500,
#                 "phone": phone_number,
#                 "message": message,
#                 "telegram_lifetime": 172800,   # 2 дня
#             }
#         ]
#     }

#     headers = {
#         "Content-Type": "application/json"
#     }
    
#     try:
#         response = requests.post(INTERCONNECT_API_URL, json=payload, headers=headers, timeout=10)
#         response_data = response.json()
#         if response.ok and response_data.get("success") is True:
#             logger.info(f"Telegram message to {phone_number} sent OK: {response_data}")
#             return True
#         else:
#             logger.error(f"Telegram message to {phone_number} failed: {response_data}")
#             return False
#     except Exception as e:
#         logger.exception(f"Ошибка при запросе в InterConnect: {e}")
#         return False
