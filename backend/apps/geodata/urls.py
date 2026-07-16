from django.urls import path

from apps.geodata.views import (
    GeocodingPreviewView,
    ImportantPlaceDetailView,
    ImportantPlaceListCreateView,
    MapContextView,
    MapListingView,
)

urlpatterns = [
    path("map/listings/", MapListingView.as_view(), name="map-listings"),
    path(
        "search-profiles/<uuid:profile_id>/important-places/",
        ImportantPlaceListCreateView.as_view(),
        name="important-place-list",
    ),
    path(
        "search-profiles/<uuid:profile_id>/important-places/geocode/",
        GeocodingPreviewView.as_view(),
        name="important-place-geocode",
    ),
    path(
        "search-profiles/<uuid:profile_id>/important-places/<uuid:place_id>/",
        ImportantPlaceDetailView.as_view(),
        name="important-place-detail",
    ),
    path(
        "search-profiles/<uuid:profile_id>/map-context/",
        MapContextView.as_view(),
        name="map-context",
    ),
]
