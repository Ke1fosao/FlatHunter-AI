from __future__ import annotations

from uuid import UUID

from celery import shared_task
from django.conf import settings
from django.utils import timezone

from apps.analysis.market_services import refresh_listing_market_assessment
from apps.analysis.models import ListingMarketAssessment, ListingRiskAssessment
from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.risk_services import refresh_listing_risk_assessment
from apps.analysis.services import refresh_listing_analysis
from apps.analysis.snapshots import capture_listing_snapshot

TASK_OPTIONS = {
    "autoretry_for": (RuntimeError,),
    "retry_backoff": True,
    "retry_jitter": True,
    "max_retries": 3,
    "soft_time_limit": 90,
    "time_limit": 120,
}


@shared_task(name="apps.analysis.tasks.capture_listing_snapshot_task", **TASK_OPTIONS)
def capture_listing_snapshot_task(listing_id: str) -> dict[str, object]:
    listing = approved_listing_queryset().get(pk=UUID(listing_id))
    result = capture_listing_snapshot(listing)
    return {
        "snapshot_id": str(result.snapshot.id),
        "created": result.created,
        "price_event_id": str(result.price_event.id) if result.price_event else None,
    }


@shared_task(name="apps.analysis.tasks.refresh_listing_market_task", **TASK_OPTIONS)
def refresh_listing_market_task(listing_id: str, force: bool = False) -> dict[str, object]:
    result = refresh_listing_market_assessment(UUID(listing_id), force=force)
    return {"assessment_id": str(result.id), "status": result.status}


@shared_task(name="apps.analysis.tasks.refresh_listing_risk_task", **TASK_OPTIONS)
def refresh_listing_risk_task(listing_id: str, force: bool = False) -> dict[str, object]:
    result = refresh_listing_risk_assessment(UUID(listing_id), force=force)
    return {"assessment_id": str(result.id), "status": result.status, "score": result.score}


@shared_task(name="apps.analysis.tasks.refresh_listing_analysis_task", **TASK_OPTIONS)
def refresh_listing_analysis_task(listing_id: str, force: bool = False) -> dict[str, object]:
    result = refresh_listing_analysis(UUID(listing_id), force=force)
    return {
        "market_assessment_id": str(result.market.id),
        "market_status": result.market.status,
        "risk_assessment_id": str(result.risk.id),
        "risk_status": result.risk.status,
        "risk_score": result.risk.score,
    }


@shared_task(name="apps.analysis.tasks.refresh_stale_listing_analyses_task", **TASK_OPTIONS)
def refresh_stale_listing_analyses_task(limit: int | None = None) -> dict[str, int]:
    configured_limit = int(getattr(settings, "ANALYSIS_BATCH_SIZE", 100))
    requested_limit = limit if limit is not None else configured_limit
    batch_size = min(max(requested_limit, 1), 500)
    now = timezone.now()
    stale_market = ListingMarketAssessment.objects.filter(valid_until__lte=now).values_list(
        "listing_id",
        flat=True,
    )
    stale_risk = ListingRiskAssessment.objects.filter(valid_until__lte=now).values_list(
        "listing_id",
        flat=True,
    )
    listing_ids = list(
        approved_listing_queryset()
        .filter(id__in=set(stale_market).union(stale_risk))
        .order_by("id")
        .values_list("id", flat=True)[:batch_size]
    )
    for listing_id in listing_ids:
        refresh_listing_analysis(listing_id, force=True)
    return {"refreshed": len(listing_ids)}
