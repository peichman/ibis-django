import re

import isbnlib
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from isbnlib import is_isbn10, is_isbn13
from nameparser import HumanName
from nameparser.config import CONSTANTS
from titlecase import titlecase

from .forms import ImportForm, SingleISBNForm
from .models import Book, Authorship, Person


def getlines(text: str) -> list[str]:
    return list(str(s) for s in filter(len, (map(str.strip, text.splitlines()))))


def index(request: HttpRequest):
    booklist = Book.objects.all()
    filtered = False

    if 'author' in request.GET:
        booklist = booklist.filter(authors__name__in=[request.GET['author']])
        filtered = True

    if 'series' in request.GET:
        booklist = booklist.filter(series__title__in=[request.GET['series']])
        filtered = True

    first_author = Authorship.objects.filter(book=OuterRef('pk'), order=1)[:1]

    booklist = booklist.order_by(Subquery(first_author.values('person__sort_name')))

    paginator = Paginator(booklist, 20)
    page_obj = paginator.get_page(request.GET.get('page', 1))

    return render(request, 'catalog/index.html', context={
        'page_obj': page_obj,
        'books': booklist,
        'filtered': filtered,
        'isbn_form': SingleISBNForm()
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
                new_book.authors.add(form.cleaned_data['author'])
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
            title = metadata.get('Title', isbn)
            if ' - ' in title:
                title, subtitle = title.split(' - ', 2)
                book.title = titlecase(title)
                book.subtitle = titlecase(subtitle)
            else:
                book.title = titlecase(title)
            book.publication_date = metadata.get('Year', '?')
            book.save()

            author_names = [HumanName(author) for author in metadata.get('Authors', [])]

            authors = []
            for author_name in author_names:
                author, _is_new = Person.objects.get_or_create(
                    name=author_name.original,
                    defaults={'sort_name': str(author_name)}
                )
                authors.append(author)

            for n, author in enumerate(authors, 1):
                book.authors.add(author, through_defaults={'order': n})

        return HttpResponseRedirect(reverse('index'))


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))
