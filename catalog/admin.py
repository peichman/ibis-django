from django.contrib import admin

from .models import Book, Person, Credit, Series, SeriesMembership, Tag


class PersonAdmin(admin.ModelAdmin):
    search_fields = ['name']


class TagAdmin(admin.ModelAdmin):
    search_fields = ['value']


class CreditInline(admin.TabularInline):
    model = Credit
    extra = 1
    autocomplete_fields = ['person']


class TaggingInline(admin.StackedInline):
    model = Book.tags.through
    extra = 1
    autocomplete_fields = ['tag']


class BookAdmin(admin.ModelAdmin):
    fields = ['title', 'subtitle', 'isbn', 'format', 'publisher', 'publication_date']
    inlines = [CreditInline, TaggingInline]
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
admin.site.register(Tag, TagAdmin)
