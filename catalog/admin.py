from django.contrib import admin

from .models import Book, Person, Credit, Series, SeriesMembership


class PersonAdmin(admin.ModelAdmin):
    search_fields = ['name']


class CreditInline(admin.TabularInline):
    model = Credit
    extra = 1
    autocomplete_fields = ['person']


class BookAdmin(admin.ModelAdmin):
    fields = ['title', 'subtitle', 'isbn', 'publisher', 'publication_date']
    inlines = [CreditInline]
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
