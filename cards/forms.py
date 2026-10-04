from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from .models import Company, Person, validate_image

class FlexibleURLField(forms.URLField):
    """Accept normal web addresses without making users type the scheme."""

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("required", False)
        kwargs.setdefault("widget", forms.TextInput(attrs={"placeholder": "example.com"}))
        super().__init__(*args, **kwargs)

    def to_python(self, value):
        value = forms.CharField.to_python(self, value)
        if value and "://" not in value:
            value = f"https://{value}"
        return value

class CompanySignupForm(forms.Form):
    company_name = forms.CharField(max_length=200, label="Company name")
    industry = forms.CharField(max_length=120, help_text="For example: Technology, legal, finance")
    logo = forms.ImageField(required=False, validators=[validate_image], help_text="JPEG, PNG, or WebP. Maximum 5 MB.")
    primary_color = forms.RegexField(r"^#[0-9A-Fa-f]{6}$", initial="#000000", widget=forms.TextInput(attrs={"type": "color"}))
    secondary_color = forms.RegexField(r"^#[0-9A-Fa-f]{6}$", initial="#ffffff", widget=forms.TextInput(attrs={"type": "color"}))
    slogan = forms.CharField(max_length=240, required=False, label="Slogan / tagline")
    phone = forms.CharField(max_length=50, required=False, label="Primary phone")
    email = forms.EmailField(label="Primary email")
    website = FlexibleURLField(label="Website")

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
class PersonLinksForm(forms.ModelForm):
    """Base person form that accepts links with or without a URL scheme."""

    website = FlexibleURLField(label="Website")
    linkedin_url = FlexibleURLField(label="LinkedIn URL")
    facebook_url = FlexibleURLField(label="Facebook URL")
    instagram_url = FlexibleURLField(label="Instagram URL")
    x_url = FlexibleURLField(label="X URL")
    youtube_url = FlexibleURLField(label="YouTube URL")
    tiktok_url = FlexibleURLField(label="TikTok URL")

    class Meta:
        model = Person
        fields = ()

class PersonForm(PersonLinksForm):
    class Meta:
        model = Person
        exclude = ("public_id", "created_at", "updated_at")

class CompanyPersonForm(PersonLinksForm):
    """Card form for company admins; the company is assigned by the view."""

    class Meta:
        model = Person
        exclude = ("company", "public_id", "is_active", "created_at", "updated_at")
