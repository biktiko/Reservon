# C:\Reservon\Reservon\reservon\utils\twilio_service.py
from twilio.rest import Client
import os


ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
WHATSAPP_NUMBER = 'whatsapp:+12545563398'

client = Client(ACCOUNT_SID, AUTH_TOKEN)

def send_whatsapp_message(to_number, content_sid, variables):
    try:
        message = client.messages.create(
            from_=WHATSAPP_NUMBER,
            to=f'whatsapp:{to_number}',
            content_sid=content_sid,
            content_variables=variables
        )
        print(f"Сообщение отправлено с SID: {message.sid}")
        return message.sid
    except Exception as e:
        print(f"Ошибка отправки сообщения: {e}")
        return None
