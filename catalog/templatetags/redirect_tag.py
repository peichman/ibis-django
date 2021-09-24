from django import template
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()


@register.simple_tag(takes_context=True)
def redirect_tag(context):
    uri = conditional_escape(context['request'].get_full_path())
    return mark_safe(f'<input type="hidden" name="redirect" value="{uri}" />')
