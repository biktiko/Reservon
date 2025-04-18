# C:\Reservon\Reservon\authentication\views.py
from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate, logout
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.shortcuts import redirect
from django.views.decorators.http import require_http_methods
from django.contrib.auth import get_backends
from django.views.decorators.cache import never_cache
import random
from django.utils import timezone
from datetime import timedelta
import requests
from django.conf import settings
import json
import re
import logging
import uuid

from .models import Profile
from .utils import send_verification_code, check_verification_code

logger = logging.getLogger('authentication')

def normalize_phone_number(phone_number):
    phone_number = phone_number.strip()
    if phone_number.startswith('0'):
        phone_number = phone_number[1:]  # убираем первый 0
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    return phone_number

@csrf_exempt
@never_cache
def load_modal(request):
    # Возвращает html модалки логина или регистрации
    if request.method == 'POST':
        data = json.loads(request.body)
        action = data.get('action')
        context = {
            'from_booking': False
        }

        try:
            if action in ['login', 'login_from_booking']:
                if action == 'login_from_booking':
                    context['from_booking'] = True
                    request.session['from_booking'] = True
                    salon_id = data.get('salon_id', None)
                    if salon_id:
                        request.session['salon_id'] = salon_id
                        
                # login_modal.html должен сам решать, показывать ли кнопку Google или нет 
                # в зависимости от ситуации (шаблон проверит login_method позже)
                html = render_to_string('authentication/login_modal.html', context, request=request)
                return JsonResponse({'html': html})
            elif action == 'register':
                # регистрация не особо актуальна, т.к. у нас логика верификации номера
                html = render_to_string('authentication/register_modal.html', context, request=request)
                return JsonResponse({'html': html})
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            logger.error(f"Error in load_modal: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

@csrf_exempt
@never_cache
def get_form(request):

    # Возвращает нужную форму в зависимости от шага (verify_code, set_password, enter_password)
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            step = data.get('step')
            phone_number = data.get('phone_number')

            if phone_number:
                phone_number = normalize_phone_number(phone_number)

            context = {
                'phone_number': phone_number,
                'from_booking': request.session.get('from_booking', False),
            }

            # Определяем пользователя
            user = None
            profile = None
            if phone_number:
                try:
                    user = User.objects.get(username=phone_number)
                    profile = user.main_profile
                except User.DoesNotExist:
                    user = None
                except Profile.DoesNotExist:
                    profile = None

            # Логика отображения форм
            if step == 'verify_code':
                html = render_to_string('authentication/verify_code.html', context, request=request)
            
            elif step == 'set_password':
                # Если пользователь уже выбрал Google - ошибка
                if user and profile and getattr(profile, 'login_method', None) == 'google':
                    return JsonResponse({'error': 'Доступен только вход через Google.', 'google_only': True}, status=400)
                html = render_to_string('authentication/set_password.html', context, request=request)
            
            elif step == 'enter_password':
                # Если пользователь уже выбрал Google - пароль не показываем
                if user and profile and getattr(profile, 'login_method', None) == 'google':
                    return JsonResponse({'error': 'Доступен только вход через Google.', 'google_only': True}, status=400)
                html = render_to_string('authentication/enter_password.html', context, request=request)

            else:
                return JsonResponse({'error': 'Invalid step.'}, status=400)
            
            return JsonResponse({'html': html})

        except json.JSONDecodeError:
            logger.error("JSON decode error in get_form", exc_info=True)
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Error in get_form: {e}", exc_info=True)
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)
    
@csrf_exempt
@never_cache
def login_view(request):
    # Начало процесса логина по номеру телефона
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')

            if not phone_number:
                return JsonResponse({'error': 'Номер телефона обязателен.'}, status=400)

            phone_number = normalize_phone_number(phone_number)

            user, user_created = User.objects.get_or_create(username=phone_number)
            if user_created:
                user.set_unusable_password()
                user.save()

            try:
                profile = Profile.objects.get(user=user)
                print('profile', profile)
            except Profile.DoesNotExist:
                if Profile.objects.filter(phone_number=phone_number).exists():
                    return JsonResponse({'error': 'Этот номер уже используется другим профилем.'}, status=400)
                else:
                    profile = Profile.objects.create(user=user, phone_number=phone_number, status='unverified')

            # Если пользователь не верифицирован, посылаем код
            
            if profile.status == 'unverified' or profile.login_method == 'sms':
                try:
                    generate_and_send_otp(profile)

                    request.session['phone_number'] = phone_number
                    return JsonResponse({'next_step': 'verify_code', 'phone_number': phone_number})
                except Exception as e:
                    logger.error(f"Failed to send verification code to {phone_number}: {e}")
                    return JsonResponse({'error': str(e)}, status=429)
            
            # Если пользователь верифицирован
            if profile.login_method == 'google':
                # Вход только через Google
                # Сразу говорим фронту, что нужен Google
                # Фронт пусть делает редирект на /accounts/google/login (где LOGIN_ON_GET включен, сразу редирект на Google)
                # Не показываем пароли
                request.session['phone_number'] = phone_number
                return JsonResponse({'google_only': True, 
                                    'phone_number': phone_number})
            
            # Если login_method=password или login_method не установлен, но пользователь уже верифицирован
            # Проверяем, есть ли пароль
            if user.has_usable_password():
                # Пользователь создан пароль ранее, просим ввести пароль
                request.session['phone_number'] = phone_number
                return JsonResponse({'next_step': 'enter_password', 'user_exists': True, 'phone_number': phone_number})
            else:
                # Пользователь верифицирован, но логин_method не google, значит можно задать пароль или выбрать Google
                request.session['phone_number'] = phone_number
                return JsonResponse({'next_step': 'set_password', 'user_exists': False, 'phone_number': phone_number})

        except json.JSONDecodeError:
            logger.error("JSON decode error in login_view")
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in login_view: {e}")
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

@csrf_exempt
def verify_code(request):
    # Проверка кода из СМС
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        code = data.get('code')

        if not phone_number or not code:
            return JsonResponse({'error': 'Номер телефона и код обязательны.'}, status=400)

        phone_number = normalize_phone_number(phone_number)

        try:
            status = check_verification_code(phone_number, code)
        except Exception as e:
            logger.error(f"Failed to verify code for {phone_number}: {e}")
            return JsonResponse({'error': 'Не удалось проверить код. Попробуйте позже.'}, status=500)

        if status == 'approved':
            try:
                user = User.objects.get(username=phone_number)
                profile = user.main_profile
                profile.status = 'verified'
                profile.save()
                request.session['phone_number'] = phone_number

                # Если пользователь уже привязал google - тогда вообще пароли не спрашиваем
                if profile.login_method != 'sms':
                    if profile.login_method == 'google':
                        # Возвращаем фронту, что нужен google
                        return JsonResponse({'google_only': True, 'phone_number': phone_number})
                    
                    # Иначе проверяем пароль
                    if user.has_usable_password():
                        next_step = 'enter_password'
                    else:
                        next_step = 'set_password'
                else:
                    # Аутентифицируем пользователя
                    login(request, user, backend='django.contrib.auth.backends.ModelBackend')
                    logger.info(f'User {phone_number} logged in successfully via SMS')

                    from_booking = request.session.get('from_booking', False)
                    salon_id = request.session.get('salon_id', None)
                    if from_booking and salon_id:
                        del request.session['from_booking']
                        del request.session['salon_id']
                        logger.debug("set_password: Redirect to booking")

                        return JsonResponse({'success': True, 'redirect_to_booking': True, 'salon_id': salon_id})
                    else:
                        return JsonResponse({'success': True, 'redirect_to_booking': False})

                return JsonResponse({'next_step': next_step, 'phone_number': phone_number})
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден.'}, status=404)
        else:
            return JsonResponse({'error': 'Неверный или истёкший код.'}, status=400)

    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

@csrf_exempt
@never_cache
def set_password(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')
            password = data.get('password')
            password_confirm = data.get('password_confirm')

            logger.debug(f"set_password called with phone_number: {phone_number}")

            if not all([phone_number, password, password_confirm]):
                logger.error("set_password: Missing fields")
                return JsonResponse({'error': 'Все поля обязательны.'}, status=400)

            if password != password_confirm:
                logger.error("set_password: Passwords do not match")
                return JsonResponse({'error': 'Пароли не совпадают.'}, status=400)

            if len(password) < 6:
                logger.error("set_password: Password too short")
                return JsonResponse({'error': 'Пароль должен быть не менее 6 символов.'}, status=400)

            phone_number = normalize_phone_number(phone_number)

            try:
                user = User.objects.get(username=phone_number)
                profile = user.main_profile
            except User.DoesNotExist:
                logger.error("set_password: User does not exist")
                return JsonResponse({'error': 'Пользователь не найден.'}, status=404)
            except Profile.DoesNotExist:
                logger.error("set_password: Profile does not exist")
                return JsonResponse({'error': 'Профиль пользователя не найден.'}, status=404)

            # Проверка метода входа
            if profile.login_method == 'google':
                logger.error("set_password: User login_method is google")
                return JsonResponse({'error': 'Доступен только вход через Google.'}, status=400)

            # Установка имени и пароля
            user.set_password(password)
            user.save()
            logger.debug("set_password: User password set")

            # Установка метода входа
            profile.login_method = 'password'
            profile.save()
            logger.debug("set_password: Profile login_method set to password")

            # Логин пользователя
            backend = get_backends()[0].__class__.__name__
            user.backend = f'django.contrib.auth.backends.{backend}'
            login(request, user)
            logger.debug("set_password: User logged in")

            # Логика перенаправления
            from_booking = request.session.get('from_booking', False)
            salon_id = request.session.get('salon_id', None)
            if from_booking and salon_id:
                del request.session['from_booking']
                del request.session['salon_id']
                logger.debug("set_password: Redirect to booking")
                return JsonResponse({'success': True, 'redirect_to_booking': True, 'salon_id': salon_id})
            else:
                logger.debug("set_password: Redirect to home")
                return JsonResponse({'success': True})
        except json.JSONDecodeError:
            logger.error("set_password: JSON decode error", exc_info=True)
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"set_password: Unexpected error: {e}", exc_info=True)
            return JsonResponse({'error': 'Internal server error.'}, status=500)

    return JsonResponse({'error': 'Invalid request method.'}, status=400)


@csrf_exempt
@never_cache
def enter_password(request):
    # Вход по паролю
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        password = data.get('password')

        if not phone_number or not password:
            return JsonResponse({'error': 'Номер телефона и пароль обязательны.'}, status=400)

        phone_number = normalize_phone_number(phone_number)

        user = authenticate(username=phone_number, password=password)
        print('enter_password view')
        print(data)
        if user is not None:
            login(request, user)
            logger.debug(f"Пользователь {phone_number} вошёл в систему.")
            print(request.session.items())
            from_booking = request.session.get('from_booking', False)
            salon_id = request.session.get('salon_id', None)
            if from_booking and salon_id:
                print('we are here')
                print('from_booking', from_booking)
                del request.session['from_booking']
                del request.session['salon_id']
                return JsonResponse({'success': True, 'redirect_to_booking': True, 'salon_id': salon_id})
            else:
                return JsonResponse({'success': True})
        else:
            return JsonResponse({'error': 'Неверный пароль.'}, status=400)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


@csrf_exempt
def resend_verification_code(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')

            if not phone_number:
                return JsonResponse({'error': 'Номер телефона обязателен.'}, status=400)

            phone_number = normalize_phone_number(phone_number)

            try:
                user = User.objects.get(username=phone_number)
                profile = user.main_profile
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден.'}, status=404)

            try:
                send_verification_code(phone_number, profile)
                return JsonResponse({'message': 'Код отправлен заново.'})
            except Exception as e:
                logger.error(f"Failed to send verification code to {phone_number}: {e}")
                return JsonResponse({'error': str(e)}, status=429)
        except json.JSONDecodeError:
            logger.error("JSON decode error in resend_verification_code")
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in resend_verification_code: {e}")
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

@require_http_methods(["GET", "POST"])
@never_cache
def custom_logout_view(request):
    logout(request)
    return redirect('/')

from django.core.cache import cache
from django.contrib.auth.decorators import user_passes_test
from django.http import HttpResponse

@user_passes_test(lambda u: u.is_superuser)
def clear_cache_view(request):
    cache.clear()
    return HttpResponse("Кэш успешно очищен.")

def generate_4_digit_code():
    return str(random.randint(1000, 9999))

def send_interconnect_sms(phone, message_text):
    # url = "https://portal.interconnect.solutions/api/v2/messages"
    url = 'https://portal.interconnect.solutions/api/json.php'

    phone_int = int(phone.lstrip('+')) # или .replace('+','') - зависит от того, как API принимает

    # Генерируем уникальный ID
    unique_id = int(uuid.uuid4().int >> 64)

    payload = {
        "auth": settings.INTERCONNECT_AUTH,
        "data": [
            {
                "type": "sms",
                "id": unique_id,
                "phone": phone_int,  
                "sms_signature": "Reservon",
                "sms_message": message_text,
                "sms_lifetime": 3600,
                "short_link": False
            }
        ]
    }

    try:
        # Укажем заголовок Content-Type: application/json
        headers = {"Content-Type": "application/json"}
        response = requests.post(url, json=payload, headers=headers)

        print("DEBUG: status_code =", response.status_code)
        print("DEBUG: raw_response =", response.text)
        try:
            response_data = response.json()
        except ValueError as ve:
            raise Exception(f"Interconnect returned non-JSON or empty response: {response.text}")


        if response.status_code == 200 and response_data.get("success") == True:
            # Проверяем data[0]["success"]
            data_items = response_data.get("data", [])
            if data_items and data_items[0].get("success") == True:
                return True
            else:
                raise Exception(f"Interconnect partial error: {response_data}")
        else:
            raise Exception(f"Interconnect error: {response_data}")
    except Exception as e:
        raise Exception(f"Failed to send SMS via Interconnect: {e}")


def generate_and_send_otp(profile):
    """
    Генерирует 4-значный код и отправляет через Interconnect.
    Сохраняет код и время истечения в profile.
    """
    code = generate_4_digit_code()
    profile.otp_code = code
    profile.otp_expires = timezone.now() + timedelta(minutes=5)  # код действителен 5 минут
    profile.save()

    # Отправляем по SMS
    message_text = f"Ваш код подтверждения от RESERVON: {code}"
    send_interconnect_sms(profile.phone_number, message_text)
