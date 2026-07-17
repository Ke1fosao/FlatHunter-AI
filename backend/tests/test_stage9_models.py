from __future__ import annotations

from decimal import Decimal

import pytest
from django.db import IntegrityError, transaction
from django.utils import timezone

from apps.analysis.models import (
    AnalysisStatus,
    ConfidenceLabel,
    ListingMarketAssessment,
    ListingPriceHistory,
    ListingRiskAssessment,
    ListingSnapshot,
    PriceDirection,
    RiskLevel,
)
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def listing(db) -> Listing:
    source = ListingSource.objects.create(
        code="stage9-models",
        display_name="Stage 9 Models",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    return Listing.objects.create(
        source=source,
        external_id="stage9-model-1",
        source_url="https://example.invalid/stage9-model-1",
        canonical_url="https://example.invalid/stage9-model-1",
        title="Тестова квартира",
        description="Синтетичне оголошення для тестування Stage 9.",
        city="Львів",
        district="Франківський",
        street="Наукова",
        price=18000,
        price_uah=18000,
        rooms=1,
        total_area=Decimal("42.00"),
        published_at=timezone.now(),
        attributes={"demo": True},
    )


def test_snapshot_hash_is_unique_per_listing(listing: Listing):
    ListingSnapshot.objects.create(
        listing=listing,
        content_hash="a" * 64,
        price_uah=listing.price_uah,
        currency="UAH",
        title_hash="b" * 64,
        description_hash="c" * 64,
        city=listing.city,
        district=listing.district,
        street=listing.street,
        rooms=listing.rooms,
        attributes_summary={"demo": True},
        is_active=True,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ListingSnapshot.objects.create(
            listing=listing,
            content_hash="a" * 64,
            price_uah=listing.price_uah,
            currency="UAH",
            title_hash="b" * 64,
            description_hash="c" * 64,
            city=listing.city,
            district=listing.district,
            street=listing.street,
            rooms=listing.rooms,
            attributes_summary={},
            is_active=True,
        )


def test_price_history_rejects_zero_change(listing: Listing):
    snapshot = ListingSnapshot.objects.create(
        listing=listing,
        content_hash="d" * 64,
        price_uah=18000,
        currency="UAH",
        title_hash="e" * 64,
        description_hash="f" * 64,
        city=listing.city,
        district=listing.district,
        street=listing.street,
        rooms=listing.rooms,
        attributes_summary={},
        is_active=True,
    )

    with pytest.raises(IntegrityError), transaction.atomic():
        ListingPriceHistory.objects.create(
            listing=listing,
            snapshot=snapshot,
            previous_price_uah=18000,
            new_price_uah=18000,
            change_amount_uah=0,
            change_percent=Decimal("0.00"),
            direction=PriceDirection.INCREASE,
            changed_at=timezone.now(),
        )


def test_market_and_risk_models_have_safe_defaults(listing: Listing):
    market = ListingMarketAssessment.objects.create(
        listing=listing,
        status=AnalysisStatus.INSUFFICIENT_DATA,
        provider="local",
        algorithm_version="market-v1",
        input_hash="1" * 64,
        comparable_count=3,
        confidence_score=Decimal("18.00"),
        confidence_label=ConfidenceLabel.LOW,
        comparable_ids=[],
        selection_summary={},
        explanation="Недостатньо схожих оголошень.",
    )
    risk = ListingRiskAssessment.objects.create(
        listing=listing,
        market_assessment=market,
        status=AnalysisStatus.READY,
        score=24,
        level=RiskLevel.LOW,
        signals=[],
        protective_signals=[],
        summary="Низький потенційний ризик.",
        safety_advice="Перевірте документи й договір перед оплатою.",
        algorithm_version="risk-v1",
        input_hash="2" * 64,
    )

    assert market.median_price_uah is None
    assert market.comparable_ids == []
    assert risk.score == 24
    assert risk.level == RiskLevel.LOW
    assert risk.signals == []
