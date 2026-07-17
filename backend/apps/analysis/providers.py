from __future__ import annotations

from django.conf import settings

from apps.analysis.comparables import select_local_comparables
from apps.analysis.contracts import ComparableSet, MarketAssessmentResult
from apps.analysis.market import calculate_market_assessment
from apps.listings.models import Listing


class MarketProviderError(RuntimeError):
    pass


class LocalDeterministicMarketProvider:
    provider_name = "local"
    model_version = "market-v1"

    def select_comparables(self, listing: Listing) -> ComparableSet:
        return select_local_comparables(listing)

    def assess(self, listing: Listing, comparables: ComparableSet) -> MarketAssessmentResult:
        return calculate_market_assessment(listing, comparables)


def get_market_provider() -> LocalDeterministicMarketProvider:
    provider = str(getattr(settings, "MARKET_ANALYSIS_PROVIDER", "local") or "local")
    if provider != "local":
        raise MarketProviderError(f"Market provider '{provider}' is not configured.")
    return LocalDeterministicMarketProvider()
