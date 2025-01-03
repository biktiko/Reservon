from django.shortcuts import render, redirect
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from authentication.models import PushSubscription
from django.views.decorators.cache import never_cache

import logging

logger = logging.getLogger('main')

@never_cache
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

            user = request.user  # Аутентифицированный пользователь

            # Проверка на существующую подписку
            existing_subscription = PushSubscription.objects.filter(user=user, endpoint=endpoint).first()
            if existing_subscription:
                # Проверяем, нужно ли обновление
                if existing_subscription.p256dh == p256dh and existing_subscription.auth == auth:
                    return JsonResponse({"success": True, "message": "Already subscribed"}, status=200)
                else:
                    # Обновляем только измененные данные
                    existing_subscription.p256dh = p256dh
                    existing_subscription.auth = auth
                    existing_subscription.save()
                    return JsonResponse({"success": True, "message": "Subscription updated"}, status=200)

            # Создаем новую подписку, если она отсутствует
            PushSubscription.objects.create(
                user=user,
                endpoint=endpoint,
                p256dh=p256dh,
                auth=auth,
            )
            return JsonResponse({"success": True, "message": "Subscribed successfully"}, status=201)

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
