from django.shortcuts import render, redirect
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from webpush.models import PushInformation, SubscriptionInfo
from django.contrib.auth.decorators import login_required
from authentication.models import PushSubscription
from django.conf import settings
from pywebpush import webpush, WebPushException

def main(request):
    return redirect('salons:salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')

def search_salons(request):
    return redirect('salons:salons_main')


@csrf_exempt
@login_required  # Убедитесь, что только аутентифицированные пользователи могут подписываться
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
        return response
    except WebPushException as ex:
        print("Ошибка при отправке push уведомления:", ex)
        # Дополнительная обработка ошибок
        if ex.response and ex.response.json():
            print("Детали ошибки:", ex.response.json())
        return None

def notify_admin_of_new_booking(booking):
    # Предположим, что вы вызываете это при создании нового бронирования
    message = json.dumps({
        "title": "Новое бронирование!",
        "body": f"Был создано новое бронирование: {booking.details}"
    })

    subscriptions = PushSubscription.objects.all()
    for subscription in subscriptions:
        subscription_info = {
            "endpoint": subscription.endpoint,
            "keys": {
                "p256dh": subscription.p256dh,
                "auth": subscription.auth
            }
        }
        send_push_notification(subscription_info, message)