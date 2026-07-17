from django.urls import path

from apps.ai_analysis.views import (
    ListingComparisonView,
    ListingOwnerQuestionsView,
    ListingSummaryView,
)

urlpatterns = [
    path("ai/listings/compare/", ListingComparisonView.as_view(), name="ai-listing-compare"),
    path(
        "ai/listings/<uuid:listing_id>/summary/",
        ListingSummaryView.as_view(),
        name="ai-listing-summary",
    ),
    path(
        "ai/listings/<uuid:listing_id>/owner-questions/",
        ListingOwnerQuestionsView.as_view(),
        name="ai-listing-owner-questions",
    ),
]
