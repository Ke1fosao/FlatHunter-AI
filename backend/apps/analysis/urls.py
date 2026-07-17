from django.urls import path

from apps.analysis.views import (
    ListingAnalysisRefreshView,
    ListingMarketAnalysisView,
    ListingPriceHistoryView,
    ListingRiskAnalysisView,
)

urlpatterns = [
    path(
        "listings/<uuid:listing_id>/price-history/",
        ListingPriceHistoryView.as_view(),
        name="listing-price-history",
    ),
    path(
        "listings/<uuid:listing_id>/market-analysis/",
        ListingMarketAnalysisView.as_view(),
        name="listing-market-analysis",
    ),
    path(
        "listings/<uuid:listing_id>/risk-analysis/",
        ListingRiskAnalysisView.as_view(),
        name="listing-risk-analysis",
    ),
    path(
        "listings/<uuid:listing_id>/analysis/refresh/",
        ListingAnalysisRefreshView.as_view(),
        name="listing-analysis-refresh",
    ),
]
