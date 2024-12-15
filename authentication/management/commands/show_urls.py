from django.core.management.base import BaseCommand
from django.urls import get_resolver

class Command(BaseCommand):
    help = 'Display all registered URLs'

    def handle(self, *args, **kwargs):
        resolver = get_resolver()

        def list_patterns(urlpatterns, prefix=""):
            for pattern in urlpatterns:
                if hasattr(pattern, 'url_patterns'):  # Если это вложенный резолвер
                    list_patterns(pattern.url_patterns, prefix + str(pattern.pattern))
                else:  # Это конечный маршрут
                    print(f"{prefix}{pattern.pattern} [name='{pattern.name}']")

        # Обрабатываем маршруты верхнего уровня
        list_patterns(resolver.url_patterns)
