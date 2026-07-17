from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.analysis.models import ListingPriceHistory, ListingSnapshot, PriceDirection
from apps.analysis.snapshots import (
    canonical_snapshot_payload,
    capture_listing_snapshot,
    snapshot_content_hash,
)
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def snapshot_listing(db) -> Listing:
    source = ListingSource.objects.create(
        code="stage9-snapshot",
        display_name="Stage 9 Snapshot",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    return Listing.objects.create(
        source=source,
        external_id="snapshot-1",
        source_url="https://example.invalid/snapshot-1",
        canonical_url="https://example.invalid/snapshot-1",
        title="Квартира для історії ціни",
        description="Детальний синтетичний опис квартири для перевірки історії ціни.",
        city="Рівне",
        district="Центр",
        street="Соборна",
        price=15000,
        price_uah=15000,
        rooms=1,
        total_area=Decimal("38.50"),
        published_at=timezone.now(),
        attributes={"demo": True, "backup_power": True, "private": "drop-me"},
    )


def test_canonical_snapshot_is_allowlisted_and_hash_is_stable(snapshot_listing: Listing):
    payload = canonical_snapshot_payload(snapshot_listing)
    same = canonical_snapshot_payload(snapshot_listing)

    assert payload["attributes_summary"] == {"backup_power": True, "demo": True}
    assert "description" not in payload
    assert snapshot_content_hash(payload) == snapshot_content_hash(same)


def test_baseline_snapshot_is_idempotent_without_fake_price_event(snapshot_listing: Listing):
    first = capture_listing_snapshot(snapshot_listing)
    second = capture_listing_snapshot(snapshot_listing)

    assert first.created is True
    assert first.price_event is None
    assert second.created is False
    assert second.snapshot == first.snapshot
    assert ListingSnapshot.objects.count() == 1
    assert ListingPriceHistory.objects.count() == 0


def test_real_price_drop_creates_one_explainable_event(snapshot_listing: Listing):
    capture_listing_snapshot(snapshot_listing)
    snapshot_listing.price = 13500
    snapshot_listing.price_uah = 13500
    snapshot_listing.save(update_fields=("price", "price_uah"))

    changed = capture_listing_snapshot(snapshot_listing)
    repeated = capture_listing_snapshot(snapshot_listing)

    assert changed.created is True
    assert changed.price_event is not None
    assert changed.price_event.direction == PriceDirection.DECREASE
    assert changed.price_event.change_amount_uah == -1500
    assert changed.price_event.change_percent == Decimal("-10.00")
    assert repeated.created is False
    assert ListingSnapshot.objects.count() == 2
    assert ListingPriceHistory.objects.count() == 1
