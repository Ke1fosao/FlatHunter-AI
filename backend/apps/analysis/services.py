from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.analysis.market_services import refresh_listing_market_assessment
from apps.analysis.models import (
    AnalysisStatus,
    ListingMarketAssessment,
    ListingRiskAssessment,
)
from apps.analysis.risk_services import refresh_listing_risk_assessment
from apps.analysis.snapshots import SnapshotCaptureResult, capture_listing_snapshot
from apps.listings.models import Listing


@dataclass(frozen=True)
class AnalysisRefreshResult:
    market: ListingMarketAssessment
    risk: ListingRiskAssessment


@transaction.atomic
def refresh_listing_analysis(
    listing_id: UUID,
    *,
    force: bool = False,
) -> AnalysisRefreshResult:
    market = refresh_listing_market_assessment(listing_id, force=force)
    risk = refresh_listing_risk_assessment(listing_id, market=market, force=force)
    return AnalysisRefreshResult(market=market, risk=risk)


def capture_and_optionally_refresh(listing_id: UUID) -> SnapshotCaptureResult:
    listing = Listing.objects.get(pk=listing_id)
    capture = capture_listing_snapshot(listing)
    if capture.created and getattr(settings, "ANALYSIS_AUTO_REFRESH_ENABLED", False):
        refresh_listing_analysis(listing_id)
    return capture


def _market_summary(market: ListingMarketAssessment | None) -> dict[str, Any]:
    if market is None:
        return {"status": "pending"}
    status = market.status
    if market.valid_until is not None and market.valid_until <= timezone.now():
        status = AnalysisStatus.STALE
    return {
        "status": status,
        "median_price_uah": market.median_price_uah,
        "q1_price_uah": market.q1_price_uah,
        "q3_price_uah": market.q3_price_uah,
        "deviation_percent": market.deviation_percent,
        "comparable_count": market.comparable_count,
        "confidence_label": market.confidence_label,
        "calculated_at": market.calculated_at,
    }


def _risk_summary(risk: ListingRiskAssessment | None) -> dict[str, Any]:
    if risk is None:
        return {"status": "pending"}
    status = risk.status
    if risk.valid_until is not None and risk.valid_until <= timezone.now():
        status = AnalysisStatus.STALE
    return {
        "status": status,
        "score": risk.score,
        "level": risk.level,
        "summary": risk.summary,
        "calculated_at": risk.calculated_at,
    }


def latest_analysis_summary(listing: Listing) -> dict[str, Any]:
    market_rows = getattr(listing, "prefetched_market_assessments", None)
    risk_rows = getattr(listing, "prefetched_risk_assessments", None)
    price_rows = getattr(listing, "prefetched_price_history", None)
    market = (
        market_rows[0]
        if market_rows
        else ListingMarketAssessment.objects.filter(listing=listing).first()
    )
    risk = (
        risk_rows[0]
        if risk_rows
        else ListingRiskAssessment.objects.filter(listing=listing).first()
    )
    price_event = price_rows[0] if price_rows else listing.price_history.first()
    return {
        "market": _market_summary(market),
        "risk": _risk_summary(risk),
        "latest_price_change": (
            {
                "previous_price_uah": price_event.previous_price_uah,
                "new_price_uah": price_event.new_price_uah,
                "change_amount_uah": price_event.change_amount_uah,
                "change_percent": price_event.change_percent,
                "direction": price_event.direction,
                "changed_at": price_event.changed_at,
            }
            if price_event is not None
            else None
        ),
    }
