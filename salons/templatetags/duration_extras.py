from django import template

register = template.Library()

@register.filter
def duration_minutes(value):
    total_seconds = int(value.total_seconds())
    minutes = total_seconds // 60
    return minutes
