from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import RedirectView
from django.views.static import serve
from django.conf import settings
urlpatterns = [
    path("", RedirectView.as_view(pattern_name="cards:dashboard", permanent=False), name="home"),
    path("admin/", admin.site.urls),
    path("", include("cards.urls")),
]
if settings.SERVE_MEDIA:
    # django.conf.urls.static.static() silently disables itself when DEBUG=False.
    # Register the media route directly so volume-backed uploads work on Railway.
    media_prefix = settings.MEDIA_URL.lstrip("/").rstrip("/")
    urlpatterns += [
        re_path(
            rf"^{media_prefix}/(?P<path>.*)$",
            serve,
            {"document_root": settings.MEDIA_ROOT},
        )
    ]
