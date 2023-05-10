import re
from urllib.parse import urlencode

from django.core.exceptions import BadRequest
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery, Q
from django.http import HttpRequest, HttpResponseRedirect, HttpResponse, Http404
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic import DetailView, TemplateView
from nameparser.config import CONSTANTS
from urlobject import URLObject

from .forms import ImportForm, SingleISBNForm, BulkEditBooksForm, BookForm
from .models import Book, Credit, Tag
from .utils import getlines, filter_group, combine, FilterSet, \
    PaginationLinks, find_object

CATEGORIES = {
    'fiction': Q(tags__value__in=['novel', 'short stories']),
    'non-fiction': ~Q(tags__value__in=['novel', 'short stories', 'poetry', 'comics', 'play']),
    'translated': Q(credit__role=Credit.Role.TRANSLATOR),
}

FILTER_TEMPLATES = {
    'category': lambda value: CATEGORIES.get(value, None),
    'format': lambda value: Q(format=value),
    'year': lambda value: Q(publication_date=value),
    'isbn': lambda value: Q(isbn=value),
    'q': lambda value: Q(title__icontains=value) | Q(persons__name__icontains=value),
    **filter_group('title'),
    **filter_group('publisher'),
    **filter_group('series', 'series__title'),
    **filter_group('tag', 'tags__value'),
    **combine(filter_group(role, value_field='persons__name', credit__role=role) for role in Credit.Role.values)
}

FILTER_LABELS = {
    'Title': 'title',
    'Author': 'author',
    'Editor': 'editor',
    'Series': 'series',
    'Tag': 'tag',
    'Publisher': 'publisher',
}

PAGE_PARAM_NAME = 'page'

PAGE_SIZE = 10


def append_filter(request: HttpRequest) -> HttpResponseRedirect:
    url = URLObject(request.build_absolute_uri())
    filter_param = request.POST['filter_name'] + request.POST['filter_operation']
    filter_value = request.POST['filter_value']
    new_url = url.add_query_param(filter_param, filter_value)
    return HttpResponseRedirect(new_url)


def index(request: HttpRequest) -> HttpResponse:
    if request.method == 'POST':
        if 'filter_name' in request.POST:
            return append_filter(request)
        else:
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

    booklist = Book.objects.all()
    filters = FilterSet()

    for filter_query in filters.build(FILTER_TEMPLATES, request.GET):
        booklist = booklist.filter(filter_query)

    first_author = Credit.objects.filter(book=OuterRef('pk'), order=1)[:1]

    booklist = booklist.distinct().order_by(
        Subquery(first_author.values('person__sort_name')),
        'publication_date'
    )

    paginator = Paginator(booklist, PAGE_SIZE)
    page = paginator.get_page(request.GET.get(PAGE_PARAM_NAME, 1))

    url = URLObject(request.build_absolute_uri())

    return render(request, 'catalog/index.html', context={
        'url': url,
        'categories': CATEGORIES.keys(),
        'filter_names': FILTER_LABELS,
        'page_obj': page,
        'filters': filters,
        'page_links': PaginationLinks(url, page, PAGE_PARAM_NAME),
        'isbn_form': SingleISBNForm()
    })


def show_book(request: HttpRequest, book_id: int):
    book = get_object_or_404(Book, pk=book_id)
    if request.method == 'GET':
        return render(request, 'catalog/book.html', context={
            'book': book,
            'isbn_form': SingleISBNForm(),
        })
    elif request.method == 'POST':
        if 'tag' in request.POST:
            tag, _ = Tag.objects.get_or_create(value=request.POST['tag'].strip())
            book.tags.add(tag)
            return HttpResponseRedirect(reverse('show_book', args=[book_id]))


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


class ImportByISBNView(TemplateView):
    template_name = 'catalog/import_by_isbn.html'

    def post(self, *_args, **_kwargs):
        if 'isbn' in self.request.POST:
            isbns = [self.request.POST['isbn']]
        elif 'isbns' in self.request.POST:
            isbns = getlines(self.request.POST['isbns'])
        else:
            isbns = []

        sort_name_format = '{last}, {title} {first} {suffix}'
        CONSTANTS.string_format = sort_name_format

        ids = [Book.create_from_isbn(isbn).id for isbn in isbns]
        if len(ids) == 1:
            url = reverse('show_book', kwargs={'book_id': ids[0]})
        else:
            url = self.request.POST.get('redirect', reverse('index'))

        return HttpResponseRedirect(url)


class BulkEditBooksView(TemplateView):
    template_name = 'catalog/bulk_edit_books.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'form': BulkEditBooksForm(),
            'books': [Book.objects.get(pk=book_id) for book_id in self.request.GET.getlist('book_id')],
            'redirect': self.request.GET['redirect']
        })

    def post(self, *_args, **_kwargs):
        book_ids = self.request.POST.getlist('book_id')
        new_format = self.request.POST['format']
        for book_id in book_ids:
            book = Book.objects.get(pk=book_id)
            book.format = new_format
            book.save()
        return HttpResponseRedirect(self.request.POST.get('redirect', reverse('index')))


def set_isbn(request, book_id):
    book = Book.objects.get(pk=book_id)
    isbn = request.POST['isbn']
    book.isbn = isbn
    book.save()
    return HttpResponseRedirect(request.POST.get('redirect', reverse('index')))


def find(request):
    uuid = request.GET['uuid']
    obj, view_name = find_object(uuid, {Book: 'show_book'})

    if obj is None:
        raise Http404(f"Could not find anything with the UUID {uuid}")

    return HttpResponseRedirect(reverse(view_name, args=[obj.id]))


class EditBookView(DetailView):
    model = Book
    context_object_name = 'book'
    template_name = 'catalog/edit_book.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['form'] = BookForm(instance=self.object)
        return context
