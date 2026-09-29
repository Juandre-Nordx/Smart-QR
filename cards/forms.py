from django import forms
from .models import Company, Person
class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        exclude = ("created_at", "updated_at")
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        exclude = ("public_id", "created_at", "updated_at")

