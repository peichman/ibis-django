from collections import namedtuple
from functools import reduce
from typing import Iterable
from urllib.parse import urlencode

import requests
from django.core.paginator import Page
from django.db.models import Q
from isbnlib import classify
from isbnlib.dev import ServiceIsDownError
from titlecase import titlecase
from urlobject import URLObject

Filter = namedtuple('Filter', ('name', 'value', 'label'))


class FilterSet:
    def __init__(self):
        self.filters = []

    def __len__(self):
        return len(self.filters)

    def __bool__(self):
        return len(self) > 0

    def __iter__(self):
        yield from self.filters

    def __getitem__(self, item):
        for f in self.filters:
            if f.name == item:
                return f
        return None

    def __repr__(self):
        params = ' '.join(f'{f.name}={f.value}' for f in self)
        return f'<{self.__class__.__name__} {params}>'

    def __str__(self):
        return urlencode([(f.name, f.value) for f in self.filters], safe='~^$') if self.filters else ''

    def add(self, name, value, label=None):
        if label is None:
            label = f'{name}: {value}'
        self.filters.append(Filter(name, value, label))


class PaginationLinks:
    def __init__(self, url: URLObject, page: Page, param_name='page'):
        self.url = url
        self.page = page
        self.param_name = param_name

    @property
    def page_number(self):
        return self.page.number

    @property
    def num_pages(self):
        return self.page.paginator.num_pages

    @property
    def first(self):
        return self.url.set_query_param(self.param_name, 1)

    @property
    def last(self):
        return self.url.set_query_param(self.param_name, self.num_pages)

    @property
    def previous(self):
        if self.page.has_previous():
            return self.url.set_query_param(self.param_name, self.page.previous_page_number())
        else:
            return None

    @property
    def next(self):
        if self.page.has_next():
            return self.url.set_query_param(self.param_name, self.page.next_page_number())
        else:
            return None


def get_classifier_tags(isbn: str) -> list[str]:
    try:
        classifiers = classify(isbn)
    except ServiceIsDownError:
        return []
    tags = []
    for system, value in classifiers.items():
        if system.lower() == 'fast':
            for number, description in value.items():
                tags.append(f'fast:{number};{description}')
        else:
            tags.append(f'{system.lower()}:{value}')
    return tags


def getlines(text: str) -> list[str]:
    return list(str(s) for s in filter(len, (map(str.strip, text.splitlines()))))


def split_title(title: str, separator: str = ' - ') -> list[str, str]:
    if separator in title:
        return [titlecase(s) for s in title.split(separator, 1)]
    else:
        return [titlecase(title), '']


def get_format(isbn):
    r = requests.get(f'https://openlibrary.org/isbn/{isbn}.json')
    return r.json().get('physical_format', '?').lower() if r.ok else '?'


class QueryTemplate:
    def __init__(self, value_field, extra_fields=None):
        if extra_fields is None:
            extra_fields = {}
        self.value_field = value_field
        self.extra_fields = extra_fields

    def __call__(self, value):
        params = {self.value_field: value}
        params.update(self.extra_fields)
        return Q(**params)

    def __repr__(self):
        return repr(self('_'))


PREDICATES = {
    '': 'iexact',
    '~': 'icontains',
    '^': 'istartswith',
    '$': 'iendswith'
}


def filter_group(param_name, value_field=None, **extra_fields):
    if value_field is None:
        value_field = param_name
    return {
        param_name + suffix: QueryTemplate(f'{value_field}__{predicate}', extra_fields)
        for suffix, predicate in PREDICATES.items()
    }


def combine(dict_iter: Iterable[dict]) -> dict:
    return reduce(lambda a, b: {**a, **b}, dict_iter)
