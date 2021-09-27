from uuid import uuid4

from django.db import models
from django.db.models import QuerySet
from isbnlib import classify


class Person(models.Model):
    name = models.CharField(max_length=256)
    sort_name = models.CharField(max_length=256)

    def __str__(self):
        return self.name

    @property
    def credits(self):
        return Credit.objects.filter(person=self.id)


class Book(models.Model):
    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, blank=True)
    persons = models.ManyToManyField(Person, through='Credit', related_name='books')
    isbn = models.CharField('ISBN', max_length=13, blank=True)
    publication_date = models.CharField(max_length=32)
    uuid = models.UUIDField('UUID', default=uuid4)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._classifiers = None

    def __str__(self):
        author_names = ', '.join(str(p) for p in self.authors)
        return f'{self.title}, by {author_names}'

    @property
    def authors(self) -> QuerySet[Person]:
        return self.persons.filter(credit__role=Credit.Role.AUTHOR).order_by('credit__order')

    def credits(self):
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

    @property
    def classifiers(self):
        if not self.isbn:
            return {}
        if self._classifiers is None:
            self._classifiers = classify(self.isbn)
        return self._classifiers


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

    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.AUTHOR)

    def __str__(self):
        return f'{self.person.name}, {self.role} of {self.book.title}'


class SeriesMembership(models.Model):
    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'Book {self.order} of {self.series.title}'
