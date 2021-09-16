from django.db import models


class Book(models.Model):
    title = models.CharField(max_length=1024)

    def __str__(self):
        return self.title
