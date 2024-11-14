# salons/utils.py

import os
import logging
from twilio.rest import Client

logger = logging.getLogger('booking')

def send_verification_code(phone_number):
    """
    Sends a verification code to the specified phone number using Twilio Verify API.
    """
    print("TWILIO_ACCOUNT_SID:", os.getenv('TWILIO_ACCOUNT_SID'))
    print("TWILIO_AUTH_TOKEN:", os.getenv('TWILIO_AUTH_TOKEN'))
    print("TWILIO_VERIFY_SERVICE_SID:", os.getenv('TWILIO_VERIFY_SERVICE_SID'))

    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    verify_service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')

    client = Client(account_sid, auth_token)

    try:
        verification = client.verify.services(verify_service_sid).verifications.create(
            to=phone_number,
            channel='sms'
        )
        logger.debug(f"Verification code sent to {phone_number}: {verification.sid}")
    except Exception as e:
        logger.error(f"Error sending verification code to {phone_number}: {e}")
        raise

def check_verification_code(phone_number, code):
    """
    Checks the verification code entered by the user using Twilio Verify API.
    """
    account_sid = os.getenv('TWILIO_ACCOUNT_SID')
    auth_token = os.getenv('TWILIO_AUTH_TOKEN')
    verify_service_sid = os.getenv('TWILIO_VERIFY_SERVICE_SID')

    client = Client(account_sid, auth_token)

    try:
        verification_check = client.verify.services(verify_service_sid).verification_checks.create(
            to=phone_number,
            code=code
        )
        logger.debug(f"Verification check for {phone_number}: {verification_check.status}")
        return verification_check.status
    except Exception as e:
        logger.error(f"Error checking verification code for {phone_number}: {e}")
        raise
