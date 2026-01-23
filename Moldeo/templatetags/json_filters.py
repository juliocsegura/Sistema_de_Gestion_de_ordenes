import json
from django import template

register = template.Library()

@register.filter
def parse_json(value):
    """Convierte un string JSON en una lista/dict de Python"""
    if not value:
        return []
    try:
        return json.loads(value)
    except (ValueError, TypeError):
        return []