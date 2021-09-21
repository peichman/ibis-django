from django.contrib import admin

from .models import Book, Person, Authorship, Series, SeriesMembership


class PersonAdmin(admin.ModelAdmin):
    search_fields = ['name']


class AuthorshipInline(admin.TabularInline):
    model = Authorship
    extra = 1
    autocomplete_fields = ['person']


class BookAdmin(admin.ModelAdmin):
    fields = ['title', 'isbn', 'uuid']
    inlines = [AuthorshipInline]
    search_fields = ['title']


class SeriesMembershipInline(admin.TabularInline):
    model = SeriesMembership
    autocomplete_fields = ['book']


class SeriesAdmin(admin.ModelAdmin):
    fields = ['title']
    inlines = [SeriesMembershipInline]


# Register your models here.
admin.site.register(Book, BookAdmin)
admin.site.register(Person, PersonAdmin)
admin.site.register(Series, SeriesAdmin)
