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
                # endpoint=endpoint, # чтобы разрешить дубликаты
                user=user,
                defaults={'p256dh': p256dh, 'auth': auth, 'user': user}
            )

            return JsonResponse({"success": True})
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({"error": "Invalid request method"}, status=400)



@csrf_exempt
def unsubscribe_push(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            endpoint = data.get('endpoint')

            if not endpoint:
                return JsonResponse({"success": False, "error": "Invalid subscription data"}, status=400)

            # Удаление подписки из базы данных
            PushSubscription.objects.filter(endpoint=endpoint).delete()

            return JsonResponse({'status': 'unsubscribed'}, status=200)
        except json.JSONDecodeError:
            return JsonResponse({"success": False, "error": "Invalid JSON"}, status=400)
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)}, status=500)
    return JsonResponse({'error': 'Invalid method'}, status=400)
