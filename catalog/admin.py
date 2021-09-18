from django.contrib import admin

from .models import Book, Person, Authorship, Series, SeriesMembership


class AuthorshipInline(admin.TabularInline):
    model = Authorship
    extra = 1


class BookAdmin(admin.ModelAdmin):
    fields = ['title', 'isbn', 'uuid']
    inlines = [AuthorshipInline]


class SeriesMembershipInline(admin.TabularInline):
    model = SeriesMembership


class SeriesAdmin(admin.ModelAdmin):
    fields = ['title']
    inlines = [SeriesMembershipInline]


# Register your models here.
admin.site.register(Book, BookAdmin)
admin.site.register(Person)
admin.site.register(Series, SeriesAdmin)
#admin.site.register(Authorship)
