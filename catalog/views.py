import re
from urllib.parse import urlencode

import isbnlib
import requests
from django.core.exceptions import BadRequest
from django.core.paginator import Paginator, Page
from django.db.models import OuterRef, Subquery, Q
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from isbnlib import is_isbn10, is_isbn13
from nameparser import HumanName
from nameparser.config import CONSTANTS
from urlobject import URLObject

from .forms import ImportForm, SingleISBNForm, BulkEditBooksForm
from .models import Book, Credit, Person, Tag
from .utils import get_classifier_tags, getlines, split_title


class FilterSet:
    def __init__(self):
        self.filters = []

    def __len__(self):
        return len(self.filters)

    def __bool__(self):
        return len(self) > 0

    def __iter__(self):
        yield from self.filters

    def __repr__(self):
        rep = '<' + self.__class__.__name__
        for name, value in self:
            rep += f' {name}={value}'
        rep += '>'
        return rep

    def __str__(self):
        return urlencode([f[:2] for f in self.filters]) if self.filters else ''

    def add(self, name, value, label=None):
        if label is None:
            label = f'{name}: {value}'
        self.filters.append((name, value, label))


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


def get_format(isbn):
    r = requests.get(f'https://openlibrary.org/isbn/{isbn}.json')
    return r.json().get('physical_format', '?').lower() if r.ok else '?'


CATEGORIES = {
    'fiction': Q(tags__value__in=['novel', 'short stories']),
    'non-fiction': ~Q(tags__value__in=['novel', 'short stories', 'poetry', 'comics', 'play']),
    'translated': Q(credit__role=Credit.Role.TRANSLATOR),
}


PREDICATES = {
    '': 'iexact',
    '~': 'icontains',
    '^': 'istartswith',
    '$': 'iendswith'
}


def create_filter(value_arg):
    def fn(_name, value):
        return Q(**{value_arg: value})
    return fn


def filter_group(param_name, query_field=None):
    if query_field is None:
        query_field = param_name
    return {
        param_name + suffix: create_filter('__'.join((query_field, predicate)))
        for suffix, predicate in PREDICATES.items()
    }


FILTER_TEMPLATES = {
    'category': lambda name, value: CATEGORIES.get(value, None),
    'tag': lambda name, value: Q(tags__value=value),
    'format': lambda name, value: Q(format=value),
    'publisher': lambda name, value: Q(publisher=value),
    'publisher~': lambda name, value: Q(publisher__icontains=value),
    'year': lambda name, value: Q(publication_date=value),
    **filter_group('series', 'series__title'),
    **filter_group('title'),
    **{role: lambda name, value: Q(credit__role=name, persons__name=value) for role in Credit.Role.values},
    **{f'{role}~': lambda name, value: Q(credit__role=name.rstrip('~'), persons__name__icontains=value) for role in
       Credit.Role.values},
}

FILTER_LABELS = {
    'Title': 'title',
    'Series': 'series'
}

PAGE_PARAM_NAME = 'page'


def append_filter(request: HttpRequest) -> HttpResponseRedirect:
    url = URLObject(request.build_absolute_uri())
    filter_param = request.POST['filter_name'] + request.POST['filter_operation']
    filter_value = request.POST['filter_value']
    new_url = url.add_query_param(filter_param, filter_value)
    return HttpResponseRedirect(new_url)


def index(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        return append_filter(request)

    booklist = Book.objects.all()
    filters = FilterSet()

    for param_name in request.GET.keys():
        if param_name in FILTER_TEMPLATES:
            for param_value in request.GET.getlist(param_name):
                filter_query = FILTER_TEMPLATES[param_name](param_name, param_value)
                if filter_query is not None:
                    booklist = booklist.filter(filter_query)
                    if param_name.endswith('~'):
                        filter_label = f'{param_name.rstrip("~")} matches "{param_value}"'
                    elif param_name.endswith('^'):
                        filter_label = f'{param_name.rstrip("^")} begins with "{param_value}"'
                    elif param_name.endswith('$'):
                        filter_label = f'{param_name.rstrip("$")} ends with "{param_value}"'
                    else:
                        filter_label = f'{param_name}: {param_value}'
                    filters.add(param_name, param_value, filter_label)

    first_author = Credit.objects.filter(book=OuterRef('pk'), order=1)[:1]

    booklist = booklist.order_by(
        Subquery(first_author.values('person__sort_name')),
        'publication_date'
    )

    paginator = Paginator(booklist, 10)
    page = paginator.get_page(request.GET.get(PAGE_PARAM_NAME, 1))

    url = URLObject(request.build_absolute_uri())

    filter_removal_links = [
        {
            'label': label,
            'href': url.del_query_param_value(name, value).del_query_param(PAGE_PARAM_NAME)
        }
        for name, value, label in filters
    ]

    return render(request, 'catalog/index.html', context={
        'url': url,
        'categories': CATEGORIES.keys(),
        'filter_names': FILTER_LABELS,
        'page_obj': page,
        'filters': filters,
        'filter_removal_links': filter_removal_links,
        'page_links': PaginationLinks(url, page, PAGE_PARAM_NAME),
        'isbn_form': SingleISBNForm()
    })


def show_book(request: HttpRequest, book_id: int):
    book = get_object_or_404(Book, pk=book_id)
    if request.method == 'GET':
        return render(request, 'catalog/book.html', context={
            'book': book
        })
    elif request.method == 'POST':
        if 'tag' in request.POST:
            tag, _ = Tag.objects.get_or_create(value=request.POST['tag'].strip())
            book.tags.add(tag)
            return HttpResponseRedirect(reverse('show_book', args=[book_id]))


def show_person(request: HttpRequest, person_id):
    person = Person.objects.get(pk=person_id)
    return render(request, 'catalog/person.html', context={
        'person': person,
        'credits': person.credits.order_by('book__publication_date')
    })


def import_books(request: HttpRequest):
    if request.method == 'GET':
        form = ImportForm()
        return render(request, 'catalog/import_books.html', context={'form': form})
    elif request.method == 'POST':
        form = ImportForm(request.POST)
        if form.is_valid():
            for title in getlines(form.cleaned_data['titles']):
                m = re.match(r'(.*?)\s*(\d{10,13})$', title)
                if m:
                    title = m[1]
                    isbn = m[2]
                else:
                    isbn = ''

                new_book = Book(title=title, isbn=isbn)
                new_book.save()
                new_book.credits.add(form.cleaned_data['author'])
            return HttpResponseRedirect(reverse('index'))


def import_by_isbn(request: HttpRequest):
    if request.method == 'GET':
        return render(request, 'catalog/import_by_isbn.html')
    elif request.method == 'POST':
        if 'isbn' in request.POST:
            isbns = [request.POST['isbn']]
        elif 'isbns' in request.POST:
            isbns = getlines(request.POST['isbns'])
        else:
            isbns = []

        sort_name_format = '{last}, {title} {first} {suffix}'
        CONSTANTS.string_format = sort_name_format

        for isbn in isbns:
            if not (is_isbn10(isbn) or is_isbn13(isbn)):
                # skip this, not an ISBN
                # TODO: log this
                continue

            book, book_is_new = Book.objects.get_or_create(isbn=isbn)

            if not book_is_new:
                # skip this book, it is already in the catalog
                # TODO: log this
                continue

            metadata = isbnlib.meta(isbn)
            # TODO: what to do if metadata is empty?

            book.title, book.subtitle = split_title(metadata.get('Title', isbn))
            book.publisher = metadata.get('Publisher') or '?'
            book.publication_date = metadata.get('Year') or '?'
            book.format = get_format(isbn)
            book.save()

            author_names = [HumanName(author) for author in metadata.get('Authors', [])]

            for i, author_name in enumerate(author_names, start=1):
                author, _is_new = Person.objects.get_or_create(
                    name=author_name.original,
                    defaults={'sort_name': str(author_name)}
                )
                book.add_author(author, order=i)

            # add tags for classifiers
            for tag_value in get_classifier_tags(isbn):
                tag, _ = Tag.objects.get_or_create(value=tag_value)
                book.tags.add(tag)

        return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))


def books(request: HttpRequest):
    if request.method == 'POST':
        action = request.POST['action']
        book_ids = request.POST.getlist('book_id')
        if action == 'tag':
            # bulk tagging
            tag_value = request.POST['tag']
            tag, _ = Tag.objects.get_or_create(value=tag_value)
            for book_id in book_ids:
                book = Book.objects.get(pk=book_id)
                book.tags.add(tag)
            return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))
        elif action == 'edit':
            # bulk editing
            qs = [('book_id', book_id) for book_id in book_ids] + [
                ('redirect', request.POST.get('redirect', reverse('index')))]
            return HttpResponseRedirect(reverse('bulk_edit_books') + '?' + urlencode(qs))
        else:
            raise BadRequest


def bulk_edit_books(request: HttpRequest):
    if request.method == 'GET':
        context = {
            'form': BulkEditBooksForm(),
            'books': [Book.objects.get(pk=book_id) for book_id in request.GET.getlist('book_id')],
            'redirect': request.GET['redirect']
        }
        return render(request, 'catalog/bulk_edit_books.html', context=context)
    elif request.method == 'POST':
        book_ids = request.POST.getlist('book_id')
        new_format = request.POST['format']
        for book_id in book_ids:
            book = Book.objects.get(pk=book_id)
            book.format = new_format
            book.save()
        return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))


def find_book(request: HttpRequest):
    isbn = request.GET.get('isbn', None) or None
    if isbn is not None:
        book = get_object_or_404(Book, isbn=isbn)
        return HttpResponseRedirect(reverse('show_book', kwargs={'book_id': book.id}))
    else:
        return HttpResponseRedirect(reverse('index'))
