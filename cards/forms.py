from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Company, Person

class CompanySignupForm(forms.Form):
    company_name = forms.CharField(max_length=200, label="Company name")
    industry = forms.CharField(max_length=120, help_text="For example: Technology, legal, finance")

class AdminSignupForm(forms.Form):
    full_name = forms.CharField(max_length=200, label="Your name")
    email = forms.EmailField(label="Work email")
    password = forms.CharField(widget=forms.PasswordInput, min_length=8)

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if get_user_model().objects.filter(username__iexact=email).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return email

    def clean_password(self):
        password = self.cleaned_data["password"]
        validate_password(password)
        return password

class SeatsSignupForm(forms.Form):
    user_count = forms.IntegerField(label="Number of users", min_value=1, max_value=10000, initial=5)

class PaymentConfirmationForm(forms.Form):
    confirm = forms.BooleanField(label="I confirm the R80 monthly company fee and R10 monthly fee per user.")

class CompanyForm(forms.ModelForm):
    class Meta:
        model = Company
        exclude = ("created_at", "updated_at")
class PersonForm(forms.ModelForm):
    class Meta:
        model = Person
        exclude = ("public_id", "created_at", "updated_at")
