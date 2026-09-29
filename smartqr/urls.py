from django.contrib import admin
from django.urls import include, path
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static
urlpatterns = [
    path("", RedirectView.as_view(pattern_name="cards:dashboard", permanent=False), name="home"),
    path("admin/", admin.site.urls),
    path("", include("cards.urls")),
]
if settings.SERVE_MEDIA:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
