from django import forms

from .models import Person


class ImportForm(forms.Form):
    author = forms.ModelChoiceField(queryset=Person.objects.all())
    titles = forms.CharField(widget=forms.Textarea)
