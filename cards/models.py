import uuid
from decimal import Decimal
from pathlib import Path
from PIL import Image
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

ALLOWED_IMAGE_TYPES = {"JPEG", "PNG", "WEBP"}
def validate_image(value):
    if not value: return
    if value.size > 5 * 1024 * 1024: raise ValidationError("Image must be 5 MB or smaller.")
    try:
        image = Image.open(value); image.verify()
        if image.format not in ALLOWED_IMAGE_TYPES: raise ValidationError("Use a JPEG, PNG, or WebP image.")
    except ValidationError: raise
    except Exception as exc: raise ValidationError("Upload a valid image.") from exc

class Company(models.Model):
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    registration_number = models.CharField(max_length=100, blank=True)
    vat_number = models.CharField(max_length=100, blank=True)
    billing_email = models.EmailField(blank=True)
    billing_contact_name = models.CharField(max_length=200, blank=True)
    billing_phone = models.CharField(max_length=50, blank=True)
    email = models.EmailField(blank=True); phone = models.CharField(max_length=50, blank=True)
    website = models.URLField(blank=True); address = models.TextField(blank=True)
    logo = models.ImageField(upload_to="companies/logos/", blank=True, validators=[validate_image])
    primary_color = models.CharField(max_length=7, default="#17324d")
    secondary_color = models.CharField(max_length=7, default="#ffffff")
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta: ordering = ["name"]
    def __str__(self): return self.name
    @property
    def active_card_count(self): return self.people.filter(is_active=True).count()
    @property
    def monthly_total(self): return Decimal("80.00") * self.active_card_count

class Person(models.Model):
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, db_index=True)
    company = models.ForeignKey(Company, related_name="people", on_delete=models.CASCADE)
    first_name = models.CharField(max_length=100); last_name = models.CharField(max_length=100)
    position = models.CharField(max_length=150, blank=True); biography = models.TextField(blank=True)
    photo = models.ImageField(upload_to="people/photos/", blank=True, validators=[validate_image])
    mobile_phone = models.CharField(max_length=50, blank=True); work_phone = models.CharField(max_length=50, blank=True)
    whatsapp_number = models.CharField(max_length=50, blank=True); email = models.EmailField(blank=True)
    website = models.URLField(blank=True); address = models.TextField(blank=True)
    linkedin_url = models.URLField(blank=True); facebook_url = models.URLField(blank=True)
    instagram_url = models.URLField(blank=True); x_url = models.URLField(blank=True)
    youtube_url = models.URLField(blank=True); tiktok_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True); updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        ordering = ["last_name", "first_name"]
        indexes = [models.Index(fields=["company", "is_active"])]
    def __str__(self): return self.full_name
    @property
    def full_name(self): return f"{self.first_name} {self.last_name}".strip()
    def get_absolute_url(self): return reverse("cards:public-card", kwargs={"public_id": self.public_id})
    def permanent_url(self): return f"{settings.PUBLIC_BASE_URL}{self.get_absolute_url()}"
