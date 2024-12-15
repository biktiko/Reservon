# authentication/adapters.py

import logging
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth.models import User
from django.shortcuts import redirect
from .models import Profile
from django.http import JsonResponse

logger = logging.getLogger('myapp.adapter')

class MySocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        logger.debug("pre_social_login вызван")
        logger.debug(f"SocialLogin object: {sociallogin}")
        logger.debug(f"Extra data from Google: {sociallogin.account.extra_data}")
        phone_number = request.session.get('phone_number')
        logger.debug(f"Номер телефона из сессии: {phone_number}")

        if not phone_number:
            logger.error("Номер телефона не найден в сессии")
            raise ImmediateHttpResponse(redirect('/auth/load_modal/?error=no_phone_in_session'))

        # Получаем или создаем пользователя
        user, created = User.objects.get_or_create(username=phone_number)
        if created:
            # Новый пользователь, сделаем пароль неудобопригодным
            user.set_unusable_password()
            user.save()
            logger.debug(f"Создан новый пользователь {user.username}")

        # Убеждаемся, что профиль существует
        try:
            profile = user.main_profile
        except Profile.DoesNotExist:
            profile = Profile.objects.create(user=user, phone_number=phone_number)
            logger.debug(f"Создан профиль для пользователя {user.username}")

        logger.debug(f"Профиль пользователя: {profile}")

        incoming_uid = sociallogin.account.uid
        logger.debug(f"Incoming Google UID: {incoming_uid}")
        logger.debug(f"extra_data: {sociallogin.account.extra_data}")

        email = sociallogin.account.extra_data.get('email')

        # Проверяем, не установлен ли login_method='password' и есть ли пароль
        if profile.login_method == 'password' and user.has_usable_password():
            logger.warning("Пользователь уже использует 'password', вход через Google запрещён")
            raise ImmediateHttpResponse(redirect('/auth/load_modal/?error=only_password_allowed'))

        if profile.login_method == 'google':
            # Уже Google-пользователь, проверим UID
            if profile.google_uid and profile.google_uid != incoming_uid:
                logger.warning("Google UID не совпадает")
                raise ImmediateHttpResponse(JsonResponse({
                    'error': 'Этот номер телефона привязан к другой учетной записи Google. Если у вас возникли сложности, свяжитесь по номеру +37443607244.'
                }, status=400))

            # Если всё хорошо, просто подключаем аккаунт
            logger.debug("Google UID совпадает, подключаем социальный аккаунт")
            sociallogin.connect(request, user)
        else:
            # Первый вход через Google
            logger.debug("Первый вход через Google, подключаем социальный аккаунт")
            sociallogin.connect(request, user)

            # Устанавливаем login_method=google, google_uid, делаем пароль неудобопригодным
            profile.login_method = 'google'
            profile.google_uid = incoming_uid
            user.set_unusable_password()

            if email:
                user.email = email
                logger.debug(f"Сохраняем email пользователя: {email}")

            user.save()
            profile.save()

            logger.debug(f"Установлен login_method=google, google_uid={profile.google_uid}, email={user.email} для пользователя {user.username}")

    def get_login_redirect_url(self, request):
        logger.debug("get_login_redirect_url вызван")
        from_booking = request.session.get('from_booking', False)
        salon_id = request.session.get('salon_id', None)
        logger.debug(f"from_booking: {from_booking}, salon_id: {salon_id}")
        if from_booking and salon_id:
            del request.session['from_booking']
            del request.session['salon_id']
            logger.debug(f"Перенаправление на /booking/finish/{salon_id}/")
            return f'/booking/finish/{salon_id}/'
        logger.debug("Перенаправление на главную страницу")
        return '/'
