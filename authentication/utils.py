# salons/utils.py

import os
import logging
from twilio.rest import Client
from django.utils import timezone
from datetime import timedelta
from authentication.models import User

logger = logging.getLogger('booking')

def send_verification_code(phone_number, profile):
    """
    Sends a verification code to the specified phone number using Twilio Verify API.
    Ensures that a new code is not sent within the cooldown period.
    """
    cooldown_period = timedelta(seconds=60)  # 60 секунд
    now = timezone.now()

    # Проверяем, прошло ли достаточно времени с последней отправки
    if profile.last_verification_sent_at and (now - profile.last_verification_sent_at) < cooldown_period:
        remaining = cooldown_period - (now - profile.last_verification_sent_at)
        raise Exception(f"Пожалуйста, подождите {int(remaining.total_seconds())} секунд перед повторной отправкой.")

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    verify_service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')

    client = Client(account_sid, auth_token)

    try:
        verification = client.verify.services(verify_service_sid).verifications.create(
            to=phone_number,
            channel='sms'
        )
        # Проверяем статус отправки
        if verification.status != 'pending':
            raise Exception(f"Twilio verification status: {verification.status}")
        
        # Обновляем время последней отправки
        profile.last_verification_sent_at = now
        profile.save()

        logger.debug(f"Verification code sent to {phone_number}: {verification.sid}")
    except Exception as e:
        # Логируем ошибку и пробрасываем исключение
        logger.error(f"Error sending verification code to {phone_number}: {e}")
        raise

def check_verification_code(phone_number, code):
    """
    Проверяем 4-значный код, который хранится у нас в БД.
    """
    try:
        user = User.objects.get(username=phone_number)
        profile = user.main_profile
        
        # Проверяем, что код совпадает и не просрочен
        if profile.otp_code == code and profile.otp_expires and profile.otp_expires > timezone.now():
            # Код ок, возвращаем 'approved'
            return 'approved'
        else:
            return 'rejected'
    except User.DoesNotExist:
        return 'rejected'

# def check_verification_code(phone_number, code):
#     """
#     Checks the verification code entered by the user using Twilio Verify API.
#     """
#     account_sid = os.getenv('TWILIO_ACCOUNT_SID')
#     auth_token = os.getenv('TWILIO_AUTH_TOKEN')
#     verify_service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')

#     client = Client(account_sid, auth_token)

#     try:
#         verification_check = client.verify.services(verify_service_sid).verification_checks.create(
#             to=phone_number,
#             code=code
#         )
#         logger.debug(f"Verification check for {phone_number}: {verification_check.status}")
#         return verification_check.status
#     except Exception as e:
#         logger.error(f"Error checking verification code for {phone_number}: {e}")
#         raise




