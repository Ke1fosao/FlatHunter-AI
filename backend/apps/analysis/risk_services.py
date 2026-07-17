from __future__ import annotations

from datetime import timedelta
from uuid import UUID

from django.conf import settings
from django.utils import timezone

from apps.analysis.contracts import RiskAssessmentResult
from apps.analysis.models import (
    AnalysisStatus,
    ListingMarketAssessment,
    ListingRiskAssessment,
    RiskLevel,
)
from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.risk import calculate_risk_assessment
from apps.analysis.snapshots import capture_listing_snapshot
from apps.analysis.utils import stable_hash
from apps.listings.models import Listing


def _ttl() -> timedelta:
    seconds = max(int(getattr(settings, "RISK_ASSESSMENT_TTL_SECONDS", 21600)), 60)
    return timedelta(seconds=seconds)


def _persist(
    *,
    listing: Listing,
    market: ListingMarketAssessment | None,
    input_hash: str,
    result: RiskAssessmentResult,
    error_code: str = "",
) -> ListingRiskAssessment:
    assessment, _ = ListingRiskAssessment.objects.update_or_create(
        listing=listing,
        input_hash=input_hash,
        defaults={
            "market_assessment": market,
            "status": result.status,
            "score": result.score,
            "level": result.level,
            "signals": [signal.to_dict() for signal in result.signals],
            "protective_signals": [signal.to_dict() for signal in result.protective_signals],
            "summary": result.summary,
            "safety_advice": result.safety_advice,
            "algorithm_version": "risk-v1",
            "valid_until": timezone.now() + _ttl(),
            "error_code": error_code,
        },
    )
    return assessment


def _disabled_result() -> RiskAssessmentResult:
    return RiskAssessmentResult(
        status=AnalysisStatus.DISABLED,
        score=0,
        level=RiskLevel.INSUFFICIENT_DATA,
        summary="Допоміжний Risk Score вимкнено в налаштуваннях.",
        safety_advice=(
            "Перевірте особу, документи, право власності й договір перед оплатою."
        ),
    )


def refresh_listing_risk_assessment(
    listing_id: UUID,
    *,
    market: ListingMarketAssessment | None = None,
    force: bool = False,
) -> ListingRiskAssessment:
    listing = approved_listing_queryset().get(pk=listing_id)
    snapshot = capture_listing_snapshot(listing).snapshot
    if market is None:
        market = ListingMarketAssessment.objects.filter(listing=listing).first()
    if not getattr(settings, "RISK_ANALYSIS_ENABLED", True):
        input_hash = stable_hash(
            {"snapshot": snapshot.content_hash, "enabled": False, "version": "risk-v1"}
        )
        return _persist(
            listing=listing,
            market=market,
            input_hash=input_hash,
            result=_disabled_result(),
        )

    price_event_ids = list(
        listing.price_history.order_by("-changed_at").values_list("id", flat=True)[:10]
    )
    input_hash = stable_hash(
        {
            "snapshot": snapshot.content_hash,
            "market": market.input_hash if market is not None else None,
            "price_events": [str(value) for value in price_event_ids],
            "version": "risk-v1",
        }
    )
    existing = ListingRiskAssessment.objects.filter(
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
    try:
        return _persist(
            listing=listing,
            market=market,
            input_hash=input_hash,
            result=calculate_risk_assessment(listing, market),
        )
    except (ValueError, ArithmeticError) as error:
        return _persist(
            listing=listing,
            market=market,
            input_hash=input_hash,
            result=RiskAssessmentResult(
                status=AnalysisStatus.FAILED,
                score=0,
                level=RiskLevel.INSUFFICIENT_DATA,
                summary="Допоміжну оцінку ризику тимчасово не вдалося розрахувати.",
                safety_advice=(
                    "Перевірте особу, документи, право власності й договір перед оплатою."
                ),
            ),
            error_code=type(error).__name__.lower(),
        )
