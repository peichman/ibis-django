import re

import isbnlib
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from nameparser import HumanName
from nameparser.config import CONSTANTS

from .forms import ImportForm
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
        'filtered': filtered
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
        new_books = {}
        new_persons = {}
        if 'isbns' in request.POST:
            isbns = getlines(request.POST['isbns'])
            sort_name_format = '{last}, {title} {first} {suffix}'
            CONSTANTS.string_format = sort_name_format

            for isbn in isbns:
                metadata = isbnlib.meta(isbn)
                author_names = [HumanName(author) for author in metadata['Authors']]
                title = metadata['Title']
                # year = metadata['Year']
                # publisher = metadata['Publisher']

                book = {
                    'title': title,
                    'isbn': isbn,
                    'authors': []
                }
                # TODO: check isbn against current database, skip existing
                for author_name in author_names:
                    name = author_name.original
                    try:
                        existing_author = Person.objects.get(name=name)
                        book['authors'].append(existing_author.id)
                    except Person.DoesNotExist:
                        sort_name = str(author_name)
                        if name not in new_persons:
                            new_persons[name] = {'name': name, 'sort_name': sort_name, 'isbns': []}
                        new_persons[name]['isbns'].append(isbn)
                        book['authors'].append(name)

                new_books[isbn] = book
        for person_data in new_persons.values():
            person = Person(name=person_data['name'], sort_name=person_data['sort_name'])
            person.save()
            for isbn in person_data['isbns']:
                book = new_books[isbn]
                i = book['authors'].index(person.name)
                book['authors'][i] = person.id

        for book_data in new_books.values():
            book = Book(title=book_data['title'], isbn=book_data['isbn'])
            book.save()
            for author_id in book_data['authors']:
                book.authors.add(author_id)

        return HttpResponseRedirect(reverse('index'))


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))
