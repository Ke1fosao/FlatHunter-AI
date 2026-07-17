from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.analysis.models import AnalysisStatus, ListingMarketAssessment, ListingRiskAssessment
from apps.analysis.services import refresh_listing_analysis
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def service_listing(db) -> Listing:
    source = ListingSource.objects.create(
        code="stage9-services",
        display_name="Stage 9 Services",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    target = Listing.objects.create(
        source=source,
        external_id="service-target",
        source_url="https://example.invalid/service-target",
        canonical_url="https://example.invalid/service-target",
        title="Service target",
        description="Synthetic detailed listing for Stage 9 orchestration tests.",
        city="Рівне",
        district="Центр",
        street="Соборна",
        price=15000,
        price_uah=15000,
        rooms=1,
        total_area=Decimal("38.00"),
        published_at=timezone.now(),
        attributes={"demo": True},
    )
    for index in range(8):
        Listing.objects.create(
            source=source,
            external_id=f"service-comparable-{index}",
            source_url=f"https://example.invalid/service-comparable-{index}",
            canonical_url=f"https://example.invalid/service-comparable-{index}",
            title=f"Service comparable {index}",
            description="Synthetic comparable with normalized and verified demo fields.",
            city="Рівне",
            district="Центр",
            street="Соборна",
            price=14000 + index * 400,
            price_uah=14000 + index * 400,
            rooms=1,
            total_area=Decimal("38.00"),
            published_at=timezone.now(),
            attributes={"demo": True},
        )
    return target


@override_settings(MARKET_MIN_COMPARABLES=4)
def test_refresh_is_idempotent_and_orders_market_before_risk(service_listing: Listing):
    first = refresh_listing_analysis(service_listing.id)
    second = refresh_listing_analysis(service_listing.id)

    assert first.market.status == AnalysisStatus.READY
    assert first.risk.market_assessment_id == first.market.id
    assert second.market.id == first.market.id
    assert second.risk.id == first.risk.id
    assert ListingMarketAssessment.objects.filter(listing=service_listing).count() == 1
    assert ListingRiskAssessment.objects.filter(listing=service_listing).count() == 1


@override_settings(MARKET_ANALYSIS_ENABLED=False, RISK_ANALYSIS_ENABLED=False)
def test_disabled_analysis_persists_safe_explicit_states(service_listing: Listing):
    result = refresh_listing_analysis(service_listing.id)

    assert result.market.status == AnalysisStatus.DISABLED
    assert result.market.median_price_uah is None
    assert result.risk.status == AnalysisStatus.DISABLED
    assert result.risk.score == 0
    assert "документ" in result.risk.safety_advice.casefold()
