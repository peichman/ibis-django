from django import template
from django.template.defaultfilters import stringfilter
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe

register = template.Library()

abbreviations = {
    'DDC': 'Dewey Decimal Classification',
    'FAST': 'Faceted Application of Subject Terminology',
    'LCC': 'Library of Congress Classification',
    'OCLC': 'Online Computer Library Center',
    'OWI': 'OCLC Work ID'
}


@register.filter
@stringfilter
def abbr(value, autoescape=True):
    esc = conditional_escape if autoescape else lambda x: x
    if value in abbreviations:
        return mark_safe(f'<abbr title="{abbreviations[value]}">{esc(value)}</abbr>')
    else:
        return mark_safe(esc(value))
