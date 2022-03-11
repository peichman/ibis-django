from django import template

register = template.Library()


@register.inclusion_tag('catalog/search_form.html')
def search_form(button_label: str = 'Search', input_size: int = 20, **filters):
    return {
        'filters': filters,
        'input_size': input_size,
        'button_label': button_label
    }
