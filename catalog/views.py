from django.http import HttpRequest
from django.shortcuts import render

from .models import Book


def index(request: HttpRequest):
    if 'author' in request.GET:
        booklist = Book.objects.filter(authors__name__in=[request.GET['author']])
    else:
        booklist = Book.objects.all()

    return render(request, 'catalog/index.html', context={'books': booklist})
