from uuid import uuid4

import isbnlib
import requests
from django.db import models
from django.db.models import QuerySet
from django.urls import reverse
from isbnlib import is_isbn10, is_isbn13
from nameparser import HumanName

from catalog.utils import split_title, get_format, get_classifier_tags


class Person(models.Model):
    name = models.CharField(max_length=256)
    sort_name = models.CharField(max_length=256)

    def __str__(self):
        return self.name

    @property
    def credits(self):
        return Credit.objects.filter(person=self.id)


class Tag(models.Model):
    value = models.CharField(max_length=1024)

    def __str__(self):
        return self.value


class CoverImage:
    def __init__(self, book: 'Book'):
        self.book = book
        self._available = None
        self._url = f'https://covers.openlibrary.org/b/isbn/{self.book.isbn}-M.jpg'

    @property
    def url(self):
        return self._url

    @property
    def is_available(self):
        if self._available is None:
            self._available = requests.head(self._url).ok
        return self._available


class Book(models.Model):
    class Format(models.TextChoices):
        HARDCOVER = 'hardcover'
        PAPERBACK = 'paperback'
        MASS_MARKET = 'mass-market paperback'
        EBOOK = 'ebook'
        MAP = 'map'
        CHAPBOOK = 'chapbook'

    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, blank=True)
    persons = models.ManyToManyField(Person, through='Credit', related_name='books')
    isbn = models.CharField('ISBN', max_length=13, blank=True)
    publisher = models.CharField(max_length=256)
    publication_date = models.CharField(max_length=32)
    format = models.CharField(max_length=32, choices=Format.choices)
    tags = models.ManyToManyField(Tag, related_name='books')
    uuid = models.UUIDField('UUID', default=uuid4)

    @classmethod
    def create_from_isbn(cls, isbn):
        if not (is_isbn10(isbn) or is_isbn13(isbn)):
            # skip this, not an ISBN
            # TODO: log this
            return

        book, book_is_new = cls.objects.get_or_create(isbn=isbn)

        if not book_is_new:
            # skip this book, it is already in the catalog
            # TODO: log this
            return

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

        return book

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.cover_image = CoverImage(self)

    def __str__(self):
        names = ', '.join(str(credit.person_with_role) for credit in self.credits())
        return f'{self.title}, by {names}'

    def credits(self) -> QuerySet['Credit']:
        return Credit.objects.filter(book=self.id).order_by('order')

    def __getattr__(self, item):
        if item in Credit.Role:
            return self.persons.filter(credit__role=item).order_by('credit__order')
        else:
            raise AttributeError(f"'{self.__class__}' object has no attribute '{item}'")

    def add_author(self, author: Person, order: int = 1):
        self.persons.add(author, through_defaults={'role': Credit.Role.AUTHOR, 'order': order})

    def series_memberships(self) -> list['SeriesMembership']:
        return self.series.through.objects.filter(book=self)

    def sorted_tags(self) -> QuerySet[Tag]:
        return self.tags.order_by('value')

    def plain_tags(self):
        return self.tags.exclude(value__contains=':').order_by('value')

    def get_absolute_url(self):
        return reverse("show_book", kwargs={"pk": self.pk})


class Series(models.Model):
    title = models.CharField(max_length=1024)
    books = models.ManyToManyField(Book, through='SeriesMembership', related_name='series')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "series"


class Credit(models.Model):
    class Role(models.TextChoices):
        AUTHOR = 'author'
        EDITOR = 'editor'
        TRANSLATOR = 'translator'
        ILLUSTRATOR = 'illustrator'
        ANNOTATOR = 'annotator'

    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AUTHOR)

    def __str__(self):
        return f'{self.person.name}, {self.role} of {self.book.title}'

    @property
    def person_with_role(self):
        output = str(self.person.name)
        if self.role != Credit.Role.AUTHOR:
            output += f' ({self.role})'
        return output


class SeriesMembership(models.Model):
    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'Book {self.order} of {self.series.title}'


class Collection(models.Model):
    title = models.CharField(max_length=1024)
    books = models.ManyToManyField(Book)

    def __str__(self):
        return self.title
