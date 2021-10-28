from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('import', views.import_books, name='import_books'),
    path('isbn_import', views.import_by_isbn, name='import_by_isbn'),
    path('books', views.books, name='books'),
    path('books/edit', views.bulk_edit_books, name='bulk_edit_books'),
    path('books/<int:book_id>', views.show_book, name='show_book'),
    path('persons/<int:person_id>', views.show_person, name='show_person'),
    path('books/<int:book_id>/isbn', views.set_isbn, name='set_isbn')
]
