from django.http import HttpRequest
from django.shortcuts import render

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
