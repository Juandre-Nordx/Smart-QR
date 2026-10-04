from django.contrib import admin
from .models import Company, Person
@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "active_card_count", "monthly_total")
    filter_horizontal = ("dashboard_users",)
@admin.register(Person)
class PersonAdmin(admin.ModelAdmin): list_display = ("full_name", "company", "is_active"); list_filter = ("company", "is_active")
