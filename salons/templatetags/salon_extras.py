from django import template
from salons.models import Salon

register = template.Library()

@register.simple_tag
def get_available_cities():
    # Получаем города из активных салонов
    return Salon.objects.filter(status='active').values_list('city', flat=True).distinct()
