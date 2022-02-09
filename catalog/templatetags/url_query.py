from django import template
from urlobject import URLObject

register = template.Library()


@register.simple_tag(takes_context=True)
def add_filter(context, name, value):
    url: URLObject = context['url'].del_query_param('page')
    filter_value = str(value)
    if filter_value in url.query_multi_dict.get(name, []):
        # filter value is already in the URL, don't need to add it
        return str(url)
    else:
        return str(url.add_query_param(name, filter_value))
