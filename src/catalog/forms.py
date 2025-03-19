from django import forms
from django.forms import ChoiceField, ModelChoiceField, CharField, TextInput

from .models import Person, Book, Credit


class ImportForm(forms.Form):
    author = forms.ModelChoiceField(queryset=Person.objects.all())
    titles = forms.CharField(widget=forms.Textarea)


class SingleISBNForm(forms.Form):
    isbn = forms.CharField(max_length=13, label='')


class BulkEditBooksForm(forms.Form):
    format = forms.ChoiceField(choices=Book.Format.choices)


class SingleTagForm(forms.Form):
    tag = forms.CharField()


class BookForm(forms.ModelForm):
    class Meta:
        model = Book
        fields = ["title", "subtitle", "publisher", "publication_date", "format", "isbn"]


class CreditForm(forms.Form):
    role = ChoiceField(choices=Credit.Role.choices)
    person = CharField(widget=TextInput(attrs={'list': 'persons'}))
