# salons/templatetags/custom_tags.py

from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

@register.filter
def concat(value, arg):
    return f"{value}{arg}"

@register.filter
def filter_salon(services, salon):
    return services.filter(salon=salon, status='active')