from __future__ import annotations

from datetime import timedelta
from decimal import Decimal
from uuid import UUID

from django.conf import settings
from django.utils import timezone

from apps.analysis.contracts import MarketAssessmentResult
from apps.analysis.models import AnalysisStatus, ConfidenceLabel, ListingMarketAssessment
from apps.analysis.providers import MarketProviderError, get_market_provider
from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.snapshots import capture_listing_snapshot
from apps.analysis.utils import stable_hash
from apps.listings.models import Listing


def _ttl() -> timedelta:
    seconds = max(int(getattr(settings, "MARKET_ASSESSMENT_TTL_SECONDS", 21600)), 60)
    return timedelta(seconds=seconds)


def _empty_result(status: str, explanation: str) -> MarketAssessmentResult:
    return MarketAssessmentResult(
        status=status,
        median_price_uah=None,
        q1_price_uah=None,
        q3_price_uah=None,
        median_price_per_sqm=None,
        target_price_per_sqm=None,
        deviation_percent=None,
        comparable_count=0,
        confidence_score=Decimal("0.00"),
        confidence_label=ConfidenceLabel.NONE,
        comparable_ids=(),
        selection_summary={},
        explanation=explanation,
    )


def _persist(
    *,
    listing: Listing,
    provider: str,
    algorithm_version: str,
    input_hash: str,
    result: MarketAssessmentResult,
    error_code: str = "",
) -> ListingMarketAssessment:
    assessment, _ = ListingMarketAssessment.objects.update_or_create(
        listing=listing,
        input_hash=input_hash,
        defaults={
            "status": result.status,
            "provider": provider,
            "algorithm_version": algorithm_version,
            "median_price_uah": result.median_price_uah,
            "q1_price_uah": result.q1_price_uah,
            "q3_price_uah": result.q3_price_uah,
            "median_price_per_sqm": result.median_price_per_sqm,
            "target_price_per_sqm": result.target_price_per_sqm,
            "deviation_percent": result.deviation_percent,
            "comparable_count": result.comparable_count,
            "confidence_score": result.confidence_score,
            "confidence_label": result.confidence_label,
            "comparable_ids": [str(value) for value in result.comparable_ids],
            "selection_summary": result.selection_summary,
            "explanation": result.explanation,
            "valid_until": timezone.now() + _ttl(),
            "error_code": error_code,
        },
    )
    return assessment


def refresh_listing_market_assessment(
    listing_id: UUID,
    *,
    force: bool = False,
) -> ListingMarketAssessment:
    listing = approved_listing_queryset().get(pk=listing_id)
    snapshot = capture_listing_snapshot(listing).snapshot
    if not getattr(settings, "MARKET_ANALYSIS_ENABLED", True):
        input_hash = stable_hash(
            {"snapshot": snapshot.content_hash, "enabled": False, "version": "market-v1"}
        )
        return _persist(
            listing=listing,
            provider="disabled",
            algorithm_version="market-v1",
            input_hash=input_hash,
            result=_empty_result(
                AnalysisStatus.DISABLED,
                "Ринковий аналіз вимкнено в налаштуваннях.",
            ),
        )

    try:
        provider = get_market_provider()
        comparables = provider.select_comparables(listing)
        input_hash = stable_hash(
            {
                "snapshot": snapshot.content_hash,
                "provider": provider.provider_name,
                "version": provider.model_version,
                "comparables": [str(value) for value in comparables.ids],
                "stage": comparables.selection_stage,
                "settings": {
                    "minimum": getattr(settings, "MARKET_MIN_COMPARABLES", 8),
                    "maximum": getattr(settings, "MARKET_MAX_COMPARABLES", 120),
                    "freshness": getattr(settings, "MARKET_FRESHNESS_DAYS", 90),
                    "radius": getattr(settings, "MARKET_RADIUS_KM", 5.0),
                    "area_tolerance": getattr(
                        settings,
                        "MARKET_AREA_TOLERANCE_PERCENT",
                        25.0,
                    ),
                },
            }
        )
        existing = ListingMarketAssessment.objects.filter(
            listing=listing,
            input_hash=input_hash,
        ).first()
        if (
            existing is not None
            and not force
            and existing.valid_until is not None
            and existing.valid_until > timezone.now()
        ):
            return existing
        return _persist(
            listing=listing,
            provider=provider.provider_name,
            algorithm_version=provider.model_version,
            input_hash=input_hash,
            result=provider.assess(listing, comparables),
        )
    except (MarketProviderError, ValueError, ArithmeticError) as error:
        provider_name = str(getattr(settings, "MARKET_ANALYSIS_PROVIDER", "local"))
        input_hash = stable_hash(
            {
                "snapshot": snapshot.content_hash,
                "provider": provider_name,
                "error": type(error).__name__,
            }
        )
        return _persist(
            listing=listing,
            provider=provider_name,
            algorithm_version="market-v1",
            input_hash=input_hash,
            result=_empty_result(
                AnalysisStatus.FAILED,
                "Ринкову оцінку тимчасово не вдалося розрахувати.",
            ),
            error_code=type(error).__name__.lower(),
        )
