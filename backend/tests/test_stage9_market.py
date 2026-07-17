from __future__ import annotations

from decimal import Decimal

import pytest
from django.test import override_settings
from django.utils import timezone

from apps.analysis.comparables import select_local_comparables
from apps.analysis.market import calculate_market_assessment
from apps.analysis.models import AnalysisStatus, ConfidenceLabel
from apps.duplicates.models import (
    ClusterMemberRole,
    ListingCluster,
    ListingClusterMember,
)
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def market_source(db) -> ListingSource:
    return ListingSource.objects.create(
        code="stage9-market",
        display_name="Stage 9 Market",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )


def make_listing(
    source: ListingSource,
    external_id: str,
    price: int,
    *,
    district: str = "Франківський",
    area: str = "40.00",
    active: bool = True,
) -> Listing:
    return Listing.objects.create(
        source=source,
        external_id=external_id,
        source_url=f"https://example.invalid/{external_id}",
        canonical_url=f"https://example.invalid/{external_id}",
        title=f"Квартира {external_id}",
        description="Синтетичне оголошення з достатньою кількістю перевірюваних деталей.",
        city="Львів",
        district=district,
        street="Наукова",
        price=price,
        price_uah=price,
        rooms=1,
        total_area=Decimal(area),
        building_type="new_building",
        renovation_level="modern",
        location_accuracy="building",
        published_at=timezone.now(),
        attributes={"demo": True},
        is_active=active,
    )


@override_settings(MARKET_MIN_COMPARABLES=4, MARKET_MAX_COMPARABLES=20)
def test_comparable_selection_excludes_target_same_cluster_and_inactive(market_source):
    target = make_listing(market_source, "target", 16000)
    duplicate = make_listing(market_source, "target-duplicate", 16100)
    cluster = ListingCluster.objects.create(primary_listing=target, member_count=2, source_count=1)
    ListingClusterMember.objects.create(
        cluster=cluster,
        listing=target,
        role=ClusterMemberRole.PRIMARY,
    )
    ListingClusterMember.objects.create(
        cluster=cluster,
        listing=duplicate,
        role=ClusterMemberRole.DUPLICATE,
    )
    inactive = make_listing(market_source, "inactive", 15900, active=False)
    comparables = [
        make_listing(market_source, f"comparable-{index}", 15000 + index * 500)
        for index in range(6)
    ]

    result = select_local_comparables(target)
    selected_ids = set(result.ids)

    assert target.id not in selected_ids
    assert duplicate.id not in selected_ids
    assert inactive.id not in selected_ids
    assert selected_ids == {listing.id for listing in comparables}
    assert result.selection_stage == "district_rooms_area"


@override_settings(MARKET_MIN_COMPARABLES=4, MARKET_MAX_COMPARABLES=20)
def test_market_statistics_are_robust_and_explain_confidence(market_source):
    target = make_listing(market_source, "target-stats", 16000)
    for index, price in enumerate((14000, 15000, 16000, 17000, 18000, 60000)):
        make_listing(market_source, f"stats-{index}", price)

    comparables = select_local_comparables(target)
    result = calculate_market_assessment(target, comparables)

    assert result.status == AnalysisStatus.READY
    assert result.median_price_uah == 16500
    assert result.q1_price_uah is not None
    assert result.q3_price_uah is not None
    assert result.comparable_count == 6
    assert result.selection_summary["outlier_count"] == 1
    assert result.confidence_label in {ConfidenceLabel.MEDIUM, ConfidenceLabel.HIGH}
    assert result.deviation_percent == Decimal("-3.03")
    assert "6" in result.explanation


@override_settings(MARKET_MIN_COMPARABLES=8, MARKET_MAX_COMPARABLES=20)
def test_insufficient_sample_does_not_return_fake_precision(market_source):
    target = make_listing(market_source, "target-small", 16000)
    for index, price in enumerate((15000, 16000, 17000)):
        make_listing(market_source, f"small-{index}", price)

    result = calculate_market_assessment(target, select_local_comparables(target))

    assert result.status == AnalysisStatus.INSUFFICIENT_DATA
    assert result.comparable_count == 3
    assert result.median_price_uah is None
    assert result.q1_price_uah is None
    assert result.q3_price_uah is None
    assert result.deviation_percent is None
