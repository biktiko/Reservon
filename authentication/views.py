# authentication/views.py

from django.http import JsonResponse
from django.template.loader import render_to_string
from django.contrib.auth import login, authenticate
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
import json
import re

from .models import Profile  # Если у вас есть модель Profile
from .utils import send_verification_code, check_verification_code  # Функции для отправки и проверки кода

import logging
logger = logging.getLogger('authentication')

def normalize_phone_number(phone_number):
    # Убираем пробелы и приводим к стандартному формату
    phone_number = phone_number.strip()
    if not phone_number.startswith('+'):
        phone_number = '+' + phone_number
    return phone_number


@csrf_exempt
def load_modal(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        print(data)
        action = data.get('action')
        context = {}

        try:
            if action in ['login', 'login_from_booking']:
                if action == 'login_from_booking':
                    context['from_booking'] = True
                    request.session['from_booking'] = True
                    salon_id = data.get('salon_id', None)
                    if salon_id:
                        request.session['salon_id'] = salon_id
                html = render_to_string('authentication/login_modal.html', context, request=request)
                return JsonResponse({'html': html})
            elif action == 'register':
                html = render_to_string('authentication/register_modal.html', context, request=request)
                return JsonResponse({'html': html})
            else:
                return JsonResponse({'error': 'Invalid action'}, status=400)
        except Exception as e:
            # Логируем ошибку и возвращаем ответ с ошибкой
            logger.error(f"Error in load_modal: {e}")
            return JsonResponse({'error': str(e)}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)



@csrf_exempt
def get_form(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            step = data.get('step')
            phone_number = data.get('phone_number')
            context = {
                'phone_number': phone_number,
                'from_booking': request.session.get('from_booking', False)
            }
            if step == 'verify_code':
                html = render_to_string('authentication/verify_code.html', context, request=request)
            elif step == 'set_password':
                html = render_to_string('authentication/set_password.html', context, request=request)
            elif step == 'enter_password':
                html = render_to_string('authentication/enter_password.html', context, request=request)
            else:
                return JsonResponse({'error': 'Invalid step.'}, status=400)
            return JsonResponse({'html': html})
        except json.JSONDecodeError:
            logger.error("JSON decode error in get_form")
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Error in get_form: {e}")
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)


@csrf_exempt
def login_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            phone_number = data.get('phone_number')

            if not phone_number:
                return JsonResponse({'error': 'Номер телефона обязателен.'}, status=400)

            # Нормализуем номер телефона
            phone_number = normalize_phone_number(phone_number)

            if not (re.match(r'^\+374\d{8}$', phone_number) or phone_number == "+15005550007"):
                return JsonResponse({'error': 'Неверный формат армянского номера телефона.'}, status=400)

            # Получаем или создаём пользователя и профиль
            user, user_created = User.objects.get_or_create(username=phone_number)
            if user_created:
                user.set_unusable_password()
                user.save()
                logger.debug(f"Создан новый пользователь: {phone_number} с неиспользуемым паролем.")

            profile, profile_created = Profile.objects.get_or_create(user=user, defaults={'phone_number': phone_number, 'status': 'unverified'})

            logger.debug(f"user.has_usable_password(): {user.has_usable_password()}")

            if profile.status == 'unverified':
                # Отправляем код верификации
                try:
                    send_verification_code(phone_number, profile)  # Передаём profile
                    request.session['phone_number'] = phone_number
                    return JsonResponse({'next_step': 'verify_code', 'phone_number': phone_number})
                except Exception as e:
                    logger.error(f"Failed to send verification code to {phone_number}: {e}")
                    return JsonResponse({'error': str(e)}, status=429)  # Статус 429 Too Many Requests
            elif not user.has_usable_password():
                # Пользователь верифицирован, но не зарегистрирован (нет пароля)
                logger.debug(f"Пользователь {phone_number} прошёл верификацию, требуется установка пароля.")
                return JsonResponse({'next_step': 'set_password', 'user_exists': False, 'phone_number': phone_number})
            else:
                # Пользователь существует и зарегистрирован, запрашиваем пароль
                logger.debug(f"Пользователь {phone_number} имеет установленный пароль. Запрос ввода пароля.")
                return JsonResponse({'next_step': 'enter_password', 'user_exists': True, 'phone_number': phone_number})

        except json.JSONDecodeError:
            logger.error("JSON decode error in login_view")
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in login_view: {e}")
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

def verify_code(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        code = data.get('code')

        if not phone_number or not code:
            return JsonResponse({'error': 'Номер телефона и код обязательны.'}, status=400)

        # Нормализуем номер телефона
        phone_number = normalize_phone_number(phone_number)

        # Проверка кода через Verify API
        try:
            status = check_verification_code(phone_number, code)
        except Exception as e:
            logger.error(f"Failed to verify code for {phone_number}: {e}")
            return JsonResponse({'error': 'Не удалось проверить код. Пожалуйста, попробуйте позже.'}, status=500)

        if status == 'approved':
            try:
                user = User.objects.get(username=phone_number)
                profile = user.main_profile  # Используем related_name='main_profile'
                profile.status = 'verified'
                profile.save()
                request.session['phone_number'] = phone_number
                logger.debug(f"Пользователь {phone_number} прошёл верификацию.")
                
                logger.debug(f"user.has_usable_password(): {user.has_usable_password()}")

                if user.has_usable_password():
                    next_step = 'enter_password'
                else:
                    next_step = 'set_password'
                
                return JsonResponse({'next_step': next_step, 'phone_number': phone_number})
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден.'}, status=404)
        else:
            return JsonResponse({'error': 'Неверный или истёкший код.'}, status=400)

    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)



def set_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        first_name = data.get('first_name')
        password = data.get('password')
        password_confirm = data.get('password_confirm')

        if not all([phone_number, first_name, password, password_confirm]):
            return JsonResponse({'error': 'Все поля обязательны.'}, status=400)

        if password != password_confirm:
            return JsonResponse({'error': 'Пароли не совпадают.'}, status=400)

        if len(password) < 6:
            return JsonResponse({'error': 'Пароль должен быть не менее 6 символов.'}, status=400)

        # Нормализуем номер телефона
        phone_number = normalize_phone_number(phone_number)

        try:
            user = User.objects.get(username=phone_number)
            user.first_name = first_name
            user.set_password(password)  # Используем метод set_password
            user.save()
            login(request, user)
            logger.debug(f"Пользователь {phone_number} установил пароль и вошёл в систему.")

            # Проверяем, пришёл ли пользователь с бронирования
            from_booking = request.session.get('from_booking', False)
            salon_id = request.session.get('salon_id', None)
            if from_booking and salon_id:
                # Удаляем флаги бронирования из сессии
                del request.session['from_booking']
                del request.session['salon_id']
                return JsonResponse({'success': True, 'redirect_to_booking': True, 'salon_id': salon_id})
            else:
                return JsonResponse({'success': True})
        except User.DoesNotExist:
            return JsonResponse({'error': 'Пользователь не найден.'}, status=404)

    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)

def enter_password(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        phone_number = data.get('phone_number')
        password = data.get('password')

        if not phone_number or not password:
            return JsonResponse({'error': 'Номер телефона и пароль обязательны.'}, status=400)

        # Нормализуем номер телефона
        phone_number = normalize_phone_number(phone_number)

        user = authenticate(username=phone_number, password=password)
        if user is not None:
            login(request, user)
            logger.debug(f"Пользователь {phone_number} вошёл в систему.")

            # Проверяем, пришёл ли пользователь с бронирования
            from_booking = request.session.get('from_booking', False)
            salon_id = request.session.get('salon_id', None)
            if from_booking and salon_id:
                # Удаляем флаги бронирования из сессии
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

            # Нормализуем номер телефона
            phone_number = normalize_phone_number(phone_number)
            
            try:
                user = User.objects.get(username=phone_number)
                profile = user.main_profile  # Используем related_name='main_profile'
            except User.DoesNotExist:
                return JsonResponse({'error': 'Пользователь не найден.'}, status=404)
            except Profile.DoesNotExist:
                # Создаём профиль, если его нет
                profile = Profile.objects.create(user=user, phone_number=phone_number, status='unverified')

            # Отправляем код верификации
            try:
                send_verification_code(phone_number, profile)  # Передаём profile
                return JsonResponse({'message': 'Код отправлен заново.'})
            except Exception as e:
                logger.error(f"Failed to send verification code to {phone_number}: {e}")
                return JsonResponse({'error': str(e)}, status=429)  # Статус 429 Too Many Requests
        except json.JSONDecodeError:
            logger.error("JSON decode error in resend_verification_code")
            return JsonResponse({'error': 'Invalid JSON.'}, status=400)
        except Exception as e:
            logger.error(f"Unexpected error in resend_verification_code: {e}")
            return JsonResponse({'error': 'Internal server error.'}, status=500)
    else:
        return JsonResponse({'error': 'Invalid request method.'}, status=400)
