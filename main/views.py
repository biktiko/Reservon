from django.shortcuts import render, redirect
import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from webpush.models import PushInformation, SubscriptionInfo
from django.contrib.auth.decorators import login_required

def main(request):
    return redirect('salons:salons_main')

def about(request):
    return render(request, 'main/about.html')

def contacts(request):
    return render(request, 'main/contacts.html')

def search_salons(request):
    return redirect('salons:salons_main')

@login_required
def subscribe_push(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            endpoint = data.get("endpoint")
            p256dh = data.get("keys", {}).get("p256dh")
            auth = data.get("keys", {}).get("auth")
            browser = data.get("browser", "")  # Опционально: можно получить из данных
            user_agent = request.META.get('HTTP_USER_AGENT', '')  # Опционально

            if not endpoint or not p256dh or not auth:
                return JsonResponse({"error": "Invalid subscription data."}, status=400)

            # Создание или обновление SubscriptionInfo
            subscription, created = SubscriptionInfo.objects.get_or_create(
                endpoint=endpoint,
                defaults={
                    "browser": browser,
                    "user_agent": user_agent,
                    "auth": auth,
                    "p256dh": p256dh,
                }
            )
            if not created:
                subscription.browser = browser
                subscription.user_agent = user_agent
                subscription.auth = auth
                subscription.p256dh = p256dh
                subscription.save()

            # Создание или обновление PushInformation
            push_info, created = PushInformation.objects.get_or_create(
                user=request.user,
                subscription=subscription
            )

            return JsonResponse({"success": True}, status=201)

        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON."}, status=400)

    return JsonResponse({"error": "Invalid request method."}, status=405)