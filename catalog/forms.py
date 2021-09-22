from django import forms

from .models import Person


class ImportForm(forms.Form):
    author = forms.ModelChoiceField(queryset=Person.objects.all())
    titles = forms.CharField(widget=forms.Textarea)


class SingleISBNForm(forms.Form):
    isbn = forms.CharField(max_length=13, label='')
