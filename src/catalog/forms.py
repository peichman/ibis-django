from django import forms

from .models import Person, Book


class ImportForm(forms.Form):
    author = forms.ModelChoiceField(queryset=Person.objects.all())
    titles = forms.CharField(widget=forms.Textarea)


class SingleISBNForm(forms.Form):
    isbn = forms.CharField(max_length=13, label='')


class BulkEditBooksForm(forms.Form):
    format = forms.ChoiceField(choices=Book.Format.choices)


class SingleTagForm(forms.Form):
    tag = forms.CharField()
