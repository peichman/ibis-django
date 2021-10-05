import re
from urllib.parse import urlencode

import isbnlib
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from isbnlib import classify, is_isbn10, is_isbn13
from isbnlib.dev import ServiceIsDownError
from nameparser import HumanName
from nameparser.config import CONSTANTS
from titlecase import titlecase

from .forms import ImportForm, SingleISBNForm
from .models import Book, Credit, Person, Tag


def getlines(text: str) -> list[str]:
    return list(str(s) for s in filter(len, (map(str.strip, text.splitlines()))))


def split_title(title: str, separator: str = ' - ') -> list[str, str]:
    if separator in title:
        return [titlecase(s) for s in title.split(separator, 1)]
    else:
        return [titlecase(title), '']


class Filters:
    def __init__(self, page=None, **filters):
        self.filters = filters
        self.page = page

    def at_page(self, page=None):
        if page is None:
            return self.filters
        else:
            return {**self.filters, 'page': page}


def index(request: HttpRequest):
    booklist = Book.objects.all()
    filters = {}

    for role in Credit.Role.values:
        if role in request.GET:
            booklist = booklist.filter(credit__role=role, persons__name__in=[request.GET[role]])
            filters[role] = request.GET[role]

    if 'series' in request.GET:
        booklist = booklist.filter(series__title__in=[request.GET['series']])
        filters['series'] = request.GET['series']

    if 'tag' in request.GET:
        booklist = booklist.filter(tags__value__contains=request.GET['tag'])
        filters['tag'] = request.GET['tag']

    first_author = Credit.objects.filter(book=OuterRef('pk'), order=1)[:1]

    booklist = booklist.order_by(
        Subquery(first_author.values('person__sort_name')),
        'publication_date'
    )

    paginator = Paginator(booklist, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))
    filter_params = Filters(**filters)

    page_link = {}
    if page_obj.has_previous():
        page_link.update({
            'first': urlencode(filter_params.at_page(1)),
            'previous': urlencode(filter_params.at_page(page_obj.previous_page_number()))
        })

    if page_obj.has_next():
        page_link.update({
            'next': urlencode(filter_params.at_page(page_obj.next_page_number())),
            'last': urlencode(filter_params.at_page(paginator.num_pages))
        })

    return render(request, 'catalog/index.html', context={
        'page_obj': page_obj,
        'filtered': len(filters) > 0,
        'page_link': page_link,
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
            if not(is_isbn10(isbn) or is_isbn13(isbn)):
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


def get_classifier_tags(isbn):
    try:
        return [f'{k.lower()}:{v}' for k, v in classify(isbn).items() if k.lower() != 'fast']
    except ServiceIsDownError:
        return []


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))
