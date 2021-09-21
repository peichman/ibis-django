import re

from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery
from django.http import HttpRequest, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .forms import ImportForm
from .models import Book, Authorship


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
            for title in form.cleaned_data['titles'].splitlines():
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


def import_by_isbn(request):
    if request.method == 'GET':
        return render(request, 'catalog/import_by_isbn.html')


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))
