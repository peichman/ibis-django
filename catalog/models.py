from uuid import uuid4

from django.db import models


class Person(models.Model):
    name = models.CharField(max_length=256)
    sort_name = models.CharField(max_length=256)

    def __str__(self):
        return self.name


class Book(models.Model):
    title = models.CharField(max_length=1024)
    authors = models.ManyToManyField(Person)
    isbn = models.CharField('ISBN', max_length=13)
    uuid = models.UUIDField('UUID', default=uuid4)

    def __str__(self):
        author_names = ', '.join(str(p) for p in self.authors.all())
        return f'{self.title}, by {author_names}'

    def author_list(self):
        return self.authors.all()
