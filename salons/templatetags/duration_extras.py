from django import template
from datetime import timedelta

register = template.Library()


@register.filter
def duration_minutes(value):
    try:
        if isinstance(value, timedelta):
            return int(value.total_seconds() // 60)
        elif isinstance(value, str):
            # Преобразуем строку в timedelta
            parts = value.split(':')
            parts = [int(part) for part in parts]
            if len(parts) == 3:
                td = timedelta(hours=parts[0], minutes=parts[1], seconds=parts[2])
            elif len(parts) == 2:
                td = timedelta(minutes=parts[0], seconds=parts[1])
            elif len(parts) == 1:
                td = timedelta(minutes=parts[0])
            else:
                return 0
            return int(td.total_seconds() // 60)
        else:
            return 0
    except Exception as e:
        # Логируем ошибку, если необходимо
        return 0
