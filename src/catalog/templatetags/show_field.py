from django import template
from django.db.models import Model

register = template.Library()


@register.inclusion_tag('catalog/show_field.html')
def show_field(obj: Model, name: str, link: bool = False):
    return {
        'obj': obj,
        'field_name': name,
        'value': getattr(obj, name, ''),
        'link': link,
    }
