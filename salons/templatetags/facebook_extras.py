# salons/templatetags/facebook_extras.py

import re
from urllib.parse import urlparse

from django import template

register = template.Library()

@register.filter
def facebook_username(url):
    """
    Пытаемся извлечь из ссылки на Facebook "красивый" ник (например, https://facebook.com/some.username).
    Возвращаем сам никнейм, если нашли. Если же ссылка ведёт на profile.php?id=... или содержит
    query-параметры, или содержит служебные пути, то возвращаем пустую строку.
    """
    if not url:
        return ""

    parsed = urlparse(url)
    # Проверяем, что домен — facebook.com
    if "facebook.com" not in parsed.netloc.lower():
        return ""

    # Извлекаем и «чистим» путь
    path = parsed.path.strip("/")  # убирает ведущий/завершающий слеш
    # Если есть query-параметры (например, ?id=...), значит точно не "красивый" URL
    if parsed.query:
        return ""

    # Если путь пустой, тоже возвращаем пустую строку
    if not path:
        return ""

    # Если путь = profile.php, groups, pages и пр., то это не "юзернейм"
    # Можете дописывать сюда свои исключения при необходимости
    forbidden_paths = {"profile.php", "pages", "groups", "watch", "events", "people"}
    if path.lower() in forbidden_paths:
        return ""

    # Наконец, проверим, что наш путь похож на ник (латиница, цифры, точки, нижнее подчеркивание)
    if re.match(r"^[A-Za-z0-9._]+$", path):
        return path  # Возвращаем "красивый" ник
    else:
        return ""
