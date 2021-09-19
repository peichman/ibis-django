from django.urls import path

from . import views


urlpatterns = [
    path('', views.index, name='index'),
    path('import', views.import_books, name='import_books'),
    path('books/<int:book_id>/isbn', views.set_isbn, name='set_isbn')
]
