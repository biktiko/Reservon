from django.shortcuts import render, redirect
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from webpush.models import PushInformation, SubscriptionInfo
from django.contrib.auth.decorators import login_required
from authentication.models import PushSubscription
from django.conf import settings
from pywebpush import webpush, WebPushException


import logging

logger = logging.getLogger('main')

def main(request):
    return redirect('salons:salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')

def search_salons(request):
    return redirect('salons:salons_main')

@csrf_exempt
@login_required
def subscribe_push(request):
    if request.method == 'POST':
        try:
            subscription = json.loads(request.body)
            endpoint = subscription.get('endpoint')
            keys = subscription.get('keys', {})
            p256dh = keys.get('p256dh')
            auth = keys.get('auth')

            if not all([endpoint, p256dh, auth]):
                return JsonResponse({"success": False, "error": "Invalid subscription data"}, status=400)

            user = request.user  # Пользователь аутентифицирован благодаря декоратору @login_required

            # Сохранение подписки в базе данных
            PushSubscription.objects.update_or_create(
                endpoint=endpoint,
                defaults={'p256dh': p256dh, 'auth': auth, 'user': user}
            )

            return JsonResponse({"success": True})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)

def send_push_notification(subscription_info, message_body):
    try:
        response = webpush(
            subscription_info=subscription_info,
            data=message_body,
            vapid_private_key=settings.WEBPUSH_SETTINGS["VAPID_PRIVATE_KEY"],
            vapid_claims={
                "sub": f"mailto:{settings.WEBPUSH_SETTINGS['VAPID_ADMIN_EMAIL']}",
            }
        )
        logger.info(f"Уведомление успешно отправлено: {response}")
        return response
    except WebPushException as ex:
        logger.error(f"Ошибка при отправке push уведомления: {ex}")
        if ex.response and ex.response.json():
            logger.error(f"Детали ошибки: {ex.response.json()}")
        return None