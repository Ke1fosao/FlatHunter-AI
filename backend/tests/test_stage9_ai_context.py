from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.ai_analysis.services import listing_context
from apps.analysis.models import (
    AnalysisStatus,
    ConfidenceLabel,
    ListingMarketAssessment,
    ListingRiskAssessment,
    RiskLevel,
)
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def ai_context_listing(db) -> Listing:
    source = ListingSource.objects.create(
        code="stage9-ai-context",
        display_name="Stage 9 AI Context",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    return Listing.objects.create(
        source=source,
        external_id="stage9-ai-context-1",
        source_url="https://example.invalid/stage9-ai-context-1",
        canonical_url="https://example.invalid/stage9-ai-context-1",
        title="AI context apartment",
        description="Synthetic listing for validated Stage 9 context tests.",
        city="Львів",
        district="Франківський",
        street="Наукова",
        price=16000,
        price_uah=16000,
        rooms=1,
        total_area=Decimal("40.00"),
        published_at=timezone.now(),
        attributes={"demo": True},
    )


def test_ai_context_uses_only_persisted_ready_stage9_values(ai_context_listing: Listing):
    market = ListingMarketAssessment.objects.create(
        listing=ai_context_listing,
        status=AnalysisStatus.READY,
        provider="local",
        algorithm_version="market-v1",
        input_hash="a" * 64,
        median_price_uah=18000,
        q1_price_uah=16500,
        q3_price_uah=19500,
        deviation_percent=Decimal("-11.11"),
        comparable_count=20,
        confidence_score=Decimal("80.00"),
        confidence_label=ConfidenceLabel.HIGH,
        comparable_ids=[],
        selection_summary={},
        explanation="Validated synthetic market result.",
        valid_until=timezone.now() + timezone.timedelta(hours=1),
    )
    ListingRiskAssessment.objects.create(
        listing=ai_context_listing,
        market_assessment=market,
        status=AnalysisStatus.READY,
        score=38,
        level=RiskLevel.REVIEW,
        signals=[],
        protective_signals=[],
        summary="Є моменти, які варто перевірити.",
        safety_advice="Перевірте документи.",
        algorithm_version="risk-v1",
        input_hash="b" * 64,
        valid_until=timezone.now() + timezone.timedelta(hours=1),
    )

    context = listing_context(ai_context_listing)

    assert context["market_median_price_uah"] == 18000
    assert context["market_deviation_percent"] == "-11.11"
    assert context["market_confidence"] == ConfidenceLabel.HIGH
    assert context["risk_score"] == 38
    assert context["risk_level"] == RiskLevel.REVIEW


def test_ai_context_keeps_insufficient_or_stale_analysis_unknown(ai_context_listing: Listing):
    market = ListingMarketAssessment.objects.create(
        listing=ai_context_listing,
        status=AnalysisStatus.INSUFFICIENT_DATA,
        provider="local",
        algorithm_version="market-v1",
        input_hash="c" * 64,
        comparable_count=3,
        confidence_score=Decimal("20.00"),
        confidence_label=ConfidenceLabel.LOW,
        comparable_ids=[],
        selection_summary={},
        explanation="Insufficient sample.",
        valid_until=timezone.now() + timezone.timedelta(hours=1),
    )
    ListingRiskAssessment.objects.create(
        listing=ai_context_listing,
        market_assessment=market,
        status=AnalysisStatus.READY,
        score=55,
        level=RiskLevel.ELEVATED,
        signals=[],
        protective_signals=[],
        summary="Stale result.",
        safety_advice="Check documents.",
        algorithm_version="risk-v1",
        input_hash="d" * 64,
        valid_until=timezone.now() - timezone.timedelta(seconds=1),
    )

    context = listing_context(ai_context_listing)

    assert context["market_median_price_uah"] is None
    assert context["market_deviation_percent"] is None
    assert context["risk_score"] is None
    assert context["risk_level"] is None
