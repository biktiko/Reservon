# account/templatetags/custom_filters.py

from django import template
from babel.dates import format_datetime
from django.utils import timezone
from django.utils.translation import get_language

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
