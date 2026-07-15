from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.searches.views import ParseNaturalLanguageView, SearchProfileViewSet

router = DefaultRouter()
router.register("search-profiles", SearchProfileViewSet, basename="search-profile")

urlpatterns = [
    path(
        "search-profiles/parse-natural-language/",
        ParseNaturalLanguageView.as_view(),
        name="parse-natural-language",
    ),
    path("", include(router.urls)),
]
