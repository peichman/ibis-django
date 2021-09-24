from uuid import uuid4

from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=256)
    sort_name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=1024)
    subtitle = models.CharField(max_length=1024, blank=True)
    authors = models.ManyToManyField(Person, through='Credit', related_name='books')
    isbn = models.CharField('ISBN', max_length=13, blank=True)
    publication_date = models.CharField(max_length=32)
    uuid = models.UUIDField('UUID', default=uuid4)

    def __str__(self):
        #author_names = ', '.join(str(p) for p in self.authors.all())
        #return f'{self.title}, by {author_names}'
        return self.title

    def author_list(self):
        return self.authors.order_by('credit__order')

    def series_memberships(self):
        return self.series.through.objects.filter(book=self)


class Series(models.Model):
    title = models.CharField(max_length=1024)
    books = models.ManyToManyField(Book, through='SeriesMembership', related_name='series')

    def __str__(self):
        return self.title

    class Meta:
        verbose_name_plural = "series"


class Credit(models.Model):
    person = models.ForeignKey(Person, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'{self.person.name} on {self.book.title}'


class SeriesMembership(models.Model):
    series = models.ForeignKey(Series, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f'Book {self.order} of {self.series.title}'
