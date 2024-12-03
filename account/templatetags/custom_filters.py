# account/templatetags/custom_filters.py

from django import template
from babel.dates import format_datetime
from django.utils import timezone
from django.utils.translation import get_language
import re

register = template.Library()

LANGUAGE_LOCALE_MAP = {
    'en': 'en',
    'ru': 'ru',
    'hy': 'hy',
}

@register.filter
def format_date_localized(value):
    if value is None:
        return ''
    tz = timezone.get_current_timezone()
    value = timezone.localtime(value, tz)
    current_language = get_language() or 'en'
    locale_code = LANGUAGE_LOCALE_MAP.get(current_language, 'en')
    return format_datetime(value, "d MMMM", locale=locale_code)

@register.filter
def format_phone(value):
    # Форматируем номер телефона
    if value and len(value) == 11:
        return f"+{value[0]} ({value[1:4]}) {value[4:7]}-{value[7:9]}-{value[9:]}"
    return value

@register.filter
def phone_number_format(value):
    """Форматирует номер телефона для использования в tel: ссылке."""
    return re.sub(r'\D', '', value)