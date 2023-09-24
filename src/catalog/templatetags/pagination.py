from django import template

register = template.Library()


@register.inclusion_tag('catalog/pagination.html', takes_context=True)
def paginate(context, page_links=None):
    if page_links is None:
        page_links = context.get('page_links')
    return {'page_links': page_links}
