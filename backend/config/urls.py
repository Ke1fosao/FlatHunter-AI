from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

from apps.core.views import health_api, health_live, health_ready

urlpatterns = [
    path("admin/", admin.site.urls),
    path("health/live/", health_live, name="health-live"),
    path("health/ready/", health_ready, name="health-ready"),
    path("api/v1/health/", health_api, name="health-api"),
    path("api/v1/", include("apps.accounts.urls")),
    path("api/v1/", include("apps.searches.urls")),
    path("api/v1/", include("apps.listings.urls")),
    path("api/v1/telegram/", include("apps.telegram_bot.urls")),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
]
