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

    market_ready = bool(
        market is not None
        and market.status == AnalysisStatus.READY
        and (market.valid_until is None or market.valid_until > now)
    )
    risk_ready = bool(
        risk is not None
        and risk.status == AnalysisStatus.READY
        and (risk.valid_until is None or risk.valid_until > now)
    )

    return {
        "market_status": market.status if market is not None else "unknown",
        "market_median_price_uah": market.median_price_uah if market_ready else None,
        "market_q1_price_uah": market.q1_price_uah if market_ready else None,
        "market_q3_price_uah": market.q3_price_uah if market_ready else None,
        "market_deviation_percent": (
            str(market.deviation_percent)
            if market_ready and market.deviation_percent is not None
            else None
        ),
        "market_confidence": market.confidence_label if market_ready else None,
        "market_comparable_count": market.comparable_count if market_ready else None,
        "risk_status": risk.status if risk is not None else "unknown",
        "risk_score": risk.score if risk_ready else None,
        "risk_level": risk.level if risk_ready else None,
        "risk_summary": risk.summary if risk_ready else None,
    }
