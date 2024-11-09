import re
from typing import Iterable, Iterator
from urllib.parse import urlencode

from django.core.exceptions import BadRequest
from django.core.paginator import Paginator
from django.db.models import OuterRef, Subquery, Q
from django.http import HttpRequest, HttpResponseRedirect, Http404, QueryDict
from django.http.response import HttpResponseRedirectBase
from django.shortcuts import render
from django.urls import reverse, reverse_lazy
from django.views import View
from django.views.generic import TemplateView, UpdateView, DetailView, FormView
from isbnlib import ISBNLibException
from nameparser.config import CONSTANTS
from urlobject import URLObject

from .forms import ImportForm, SingleISBNForm, SingleTagForm, BookForm
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


class IndexView(View):
    def post(self, _request):
        if 'filter_name' in self.request.POST:
            return append_filter(self.request)
        else:
            action = self.request.POST['action']
            book_ids = self.request.POST.getlist('book_id')
            if action == 'tag':
                # bulk tagging
                tag_value = self.request.POST['tag']
                tag, _ = Tag.objects.get_or_create(value=tag_value)
                for book_id in book_ids:
                    book = Book.objects.get(pk=book_id)
                    book.tags.add(tag)
                return HttpResponseRedirect(self.request.POST.get('redirect', reverse('index')))
            elif action == 'edit':
                # bulk editing
                qs = [('book_id', book_id) for book_id in book_ids] + [
                    ('redirect', self.request.POST.get('redirect', reverse('index')))]
                return HttpResponseRedirect(reverse('bulk_edit_books') + '?' + urlencode(qs))
            else:
                raise BadRequest

    def get(self, _request):
        booklist = Book.objects.all()
        filters = FilterSet()

        for filter_query in filters.build(FILTER_TEMPLATES, self.request.GET):
            booklist = booklist.filter(filter_query)

        first_author = Credit.objects.filter(book=OuterRef('pk'), order=1)[:1]

        booklist = booklist.distinct().order_by(
            Subquery(first_author.values('person__sort_name')),
            'publication_date'
        )

        paginator = Paginator(booklist, PAGE_SIZE)
        page = paginator.get_page(self.request.GET.get(PAGE_PARAM_NAME, 1))

        url = URLObject(self.request.build_absolute_uri())

        return render(self.request, 'catalog/index.html', context={
            'url': url,
            'categories': CATEGORIES.keys(),
            'filter_names': FILTER_LABELS,
            'page_obj': page,
            'filters': filters,
            'page_links': PaginationLinks(url, page, PAGE_PARAM_NAME),
            'isbn_form': SingleISBNForm()
        })


class BookView(DetailView):
    model = Book
    template_name = 'catalog/book.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'tag_form': SingleTagForm(),
            'isbn_form': SingleISBNForm(),
        })
        return context


class BookTagsView(FormView):
    form_class = SingleTagForm

    def form_valid(self, form):
        tag, _ = Tag.objects.get_or_create(value=form.cleaned_data['tag'])
        book = Book.objects.all().get(pk=self.kwargs['pk'])
        book.tags.add(tag)
        return HttpResponseRedirect(reverse('show_book', args=[book.pk]))


class ImportBooksView(FormView):
    form_class = ImportForm
    template_name = 'catalog/import_books.html'
    success_url = reverse_lazy('index')

    def form_valid(self, form):
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
        return super().form_valid(form)


class ImportByISBNView(TemplateView):
    template_name = 'catalog/import_by_isbn.html'

    def post(self, _request):
        if 'isbn' in self.request.POST:
            isbns = [self.request.POST['isbn']]
        elif 'isbns' in self.request.POST:
            isbns = getlines(self.request.POST['isbns'])
        else:
            isbns = []

        sort_name_format = '{last}, {title} {first} {suffix}'
        CONSTANTS.string_format = sort_name_format

        import_results = []
        for isbn in isbns:
            try:
                book = Book.create_from_isbn(isbn)
                import_results.append({
                    'isbn': isbn,
                    'success': True,
                    'id': book.id,
                    'title': book.title,
                })
            except ISBNLibException as e:
                import_results.append({
                    'isbn': isbn,
                    'success': False,
                    'message': str(e),
                })

        if len(import_results) == 1 and import_results[0]['success']:
            url = reverse('show_book', kwargs={'pk': import_results[0]['id']})
            return HttpResponseRedirect(url)
        else:
            return render(self.request, 'catalog/import_results.html', context={'results': import_results})
            #url = self.request.POST.get('redirect', reverse('index'))



class BulkEditBooksView(FormView):
    form_class = BookForm
    template_name = 'catalog/bulk_edit_books.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        books = Book.objects.filter(id__in=self.request.GET.getlist('book_id'))
        context.update({
            'forms': [BookForm(instance=book) for book in books],
            'books': books,
            'redirect': self.request.GET['redirect']
        })
        return context

    def post(self, request, *args, **kwargs):
        field_keys = ('book_id', 'title', 'subtitle', 'publisher', 'publication_date')

        for row in build_rows(self.request.POST, field_keys):
            pk = row.pop('book_id')
            book = Book.objects.get(pk=pk)
            for k, v in row.items():
                setattr(book, k, v)
            book.save()

        return HttpResponseRedirect(self.request.POST.get('redirect', reverse('index')))


def build_rows(post_data: QueryDict, field_keys: Iterable[str]) -> Iterator[dict[str, str]]:
    yield from (dict(zip(field_keys, row_values)) for row_values in build_row_values_iter(post_data, field_keys))


def build_row_values_iter(post_data: QueryDict, fields: Iterable[str]) -> Iterator[Iterable[str]]:
    """Transform a query dictionary with data keyed by field to an iterator
    that yields tuples with the nth value of each field, in the order of
    the fields iterable.

    This is essentially "rotating" tabular data that is initially keyed
    by column into groups by row."""
    yield from zip(*(post_data.getlist(field) for field in fields))


def find(request):
    uuid = request.GET['uuid']
    obj, view_name = find_object(uuid, {Book: 'show_book'})

    if obj is None:
        raise Http404(f"Could not find anything with the UUID {uuid}")

    return HttpResponseRedirect(reverse(view_name, args=[obj.id]))


class EditBookView(UpdateView):
    model = Book
    fields = ["title", "publisher", "publication_date", "format"]
    template_name = 'catalog/edit_book.html'


class BookFieldView(DetailView):
    model = Book
    template_name = 'catalog/show_field.html'
    context_object_name = 'book'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = self.get_object()
        field_name = self.kwargs.get('field')
        context.update(
            field_name=field_name,
            value=getattr(book, field_name),
            link=(field_name in ('publisher', 'publication_date', 'format')),
        )
        return context


class HttpResponseSeeOther(HttpResponseRedirectBase):
    status_code = 303


class EditBookFieldView(TemplateView):
    template_name = 'catalog/edit_field.html'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        book = Book.objects.get(pk=self.kwargs.get('pk'))
        field_name = self.kwargs.get('field')
        form = BookForm(instance=book)
        field = form.fields[field_name]
        context.update(
            book=book,
            field_name=field_name,
            field=field.get_bound_field(form, field_name),
            url=reverse('edit_book_field', args=(book.id, field_name)),
        )
        return context

    def post(self, _request, pk: int, field: str):
        book = Book.objects.get(pk=pk)
        value = self.request.POST[field]
        setattr(book, field, value)
        book.save()
        return HttpResponseSeeOther(reverse('book_field', kwargs={'pk': pk, 'field': field}))
