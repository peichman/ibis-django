from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('import', views.import_books, name='import_books'),
    path('isbn_import', views.ImportByISBNView.as_view(), name='import_by_isbn'),
    path('records', views.BulkEditBooksView.as_view(), name='bulk_edit_books'),
    path('<int:book_id>', views.show_book, name='show_book'),
    path('<int:pk>/record', views.EditBookView.as_view(), name='edit_book'),
    path('find', views.find, name='find'),
]
