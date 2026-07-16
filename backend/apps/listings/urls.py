from django.urls import include, path
from rest_framework.routers import DefaultRouter

from apps.listings.views import ListingViewSet

router = DefaultRouter()
router.register("listings", ListingViewSet, basename="listing")

urlpatterns = [path("", include(router.urls))]
