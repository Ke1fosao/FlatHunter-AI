from rest_framework.routers import DefaultRouter

from apps.duplicates.views import DuplicateCandidateViewSet, ListingClusterViewSet

router = DefaultRouter()
router.register("listing-clusters", ListingClusterViewSet, basename="listing-cluster")
router.register("duplicate-candidates", DuplicateCandidateViewSet, basename="duplicate-candidate")

urlpatterns = router.urls
