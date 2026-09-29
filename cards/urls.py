from django.urls import path
from . import views
app_name = "cards"
urlpatterns = [
 path("health/", views.health, name="health"), path("dashboard/", views.dashboard, name="dashboard"),
 path("dashboard/people/", views.people, name="people"), path("dashboard/companies/new/", views.company_create, name="company-create"),
 path("dashboard/companies/<int:pk>/edit/", views.company_edit, name="company-edit"), path("dashboard/people/new/", views.person_create, name="person-create"),
 path("dashboard/people/<int:pk>/edit/", views.person_edit, name="person-edit"), path("dashboard/people/<int:pk>/toggle/", views.toggle_person, name="person-toggle"),
 path("c/<uuid:public_id>/", views.public_card, name="public-card"), path("c/<uuid:public_id>/contact.vcf", views.vcard, name="vcard"),
 path("c/<uuid:public_id>/qr.<str:kind>", views.qr_download, name="qr"),
]
