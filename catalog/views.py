import re

from django.http import HttpRequest, HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from .forms import ImportForm
from .models import Book


def index(request: HttpRequest):
    if 'author' in request.GET:
        booklist = Book.objects.filter(authors__name__in=[request.GET['author']])
        filtered = True
    elif 'series' in request.GET:
        booklist = Book.objects.filter(series__title__in=[request.GET['series']])
        filtered = True
    else:
        booklist = Book.objects.all()
        filtered = False

    return render(request, 'catalog/index.html', context={'books': booklist, 'filtered': filtered})


def import_books(request: HttpRequest):
    if request.method == 'GET':
        form = ImportForm()
        return render(request, 'catalog/import_books.html', context={'form': form})
    elif request.method == 'POST':
        form = ImportForm(request.POST)
        if form.is_valid():
            for title in form.cleaned_data['titles'].splitlines():
                m = re.match(r'(.*?)\s*(\d{13})$', title)
                if m:
                    title = m[1]
                    isbn = m[2]
                else:
                    isbn = ''

                new_book = Book(title=title, isbn=isbn)
                new_book.save()
                new_book.authors.add(form.cleaned_data['author'])
            return HttpResponseRedirect(reverse('index'))
