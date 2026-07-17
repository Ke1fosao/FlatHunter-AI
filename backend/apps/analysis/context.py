from __future__ import annotations

from typing import Any

from django.utils import timezone

from apps.analysis.models import AnalysisStatus, ListingMarketAssessment, ListingRiskAssessment
from apps.listings.models import Listing


def validated_analysis_context(listing: Listing) -> dict[str, Any]:
    """Return persisted, non-stale Stage 9 facts suitable for AI context.

    Stage 8 may explain these values, but it must never recompute market or risk
    scores. Missing, disabled, failed, insufficient, or stale assessments remain
    explicit unknowns.
    """

    now = timezone.now()
    market = ListingMarketAssessment.objects.filter(listing=listing).first()
    risk = ListingRiskAssessment.objects.filter(listing=listing).first()

    market_ready = (
        market
        if market is not None
        and market.status == AnalysisStatus.READY
        and (market.valid_until is None or market.valid_until > now)
        else None
    )
    risk_ready = (
        risk
        if risk is not None
        and risk.status == AnalysisStatus.READY
        and (risk.valid_until is None or risk.valid_until > now)
        else None
    )

    return {
        "market_status": market.status if market is not None else "unknown",
        "market_median_price_uah": (
            market_ready.median_price_uah if market_ready is not None else None
        ),
        "market_q1_price_uah": market_ready.q1_price_uah if market_ready is not None else None,
        "market_q3_price_uah": market_ready.q3_price_uah if market_ready is not None else None,
        "market_deviation_percent": (
            str(market_ready.deviation_percent)
            if market_ready is not None and market_ready.deviation_percent is not None
            else None
        ),
        "market_confidence": (
            market_ready.confidence_label if market_ready is not None else None
        ),
        "market_comparable_count": (
            market_ready.comparable_count if market_ready is not None else None
        ),
        "risk_status": risk.status if risk is not None else "unknown",
        "risk_score": risk_ready.score if risk_ready is not None else None,
        "risk_level": risk_ready.level if risk_ready is not None else None,
        "risk_summary": risk_ready.summary if risk_ready is not None else None,
    }
