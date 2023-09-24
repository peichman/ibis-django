from django.urls import path

from . import views

urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),
    path('import', views.ImportBooksView.as_view(), name='import_books'),
    path('isbn_import', views.ImportByISBNView.as_view(), name='import_by_isbn'),
    path('records', views.BulkEditBooksView.as_view(), name='bulk_edit_books'),
    path('<int:pk>', views.BookView.as_view(), name='show_book'),
    path('<int:pk>/metadata', views.EditBookView.as_view(), name='edit_book'),
    path('<int:pk>/tags', views.BookTagsView.as_view(), name='book_tags'),
    path('find', views.find, name='find'),
]
