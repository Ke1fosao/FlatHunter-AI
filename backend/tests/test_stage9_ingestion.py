from __future__ import annotations

import pytest
from asgiref.sync import async_to_sync

from apps.analysis.models import ListingPriceHistory, ListingSnapshot
from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.services import ingest_source


@pytest.mark.django_db(transaction=True)
def test_demo_ingestion_captures_baseline_then_real_revision_changes():
    adapter = DemoListingSourceAdapter()

    first = async_to_sync(ingest_source)(
        adapter,
        SourceSearchRequest(limit=24, seed=20260716, revision=1),
    )
    baseline_snapshots = ListingSnapshot.objects.count()
    baseline_events = ListingPriceHistory.objects.count()

    second = async_to_sync(ingest_source)(
        adapter,
        SourceSearchRequest(limit=24, seed=20260716, revision=2),
    )

    assert first.created == 24
    assert baseline_snapshots == 24
    assert baseline_events == 0
    assert second.updated > 0
    assert ListingSnapshot.objects.count() > baseline_snapshots
    assert ListingPriceHistory.objects.filter(direction="decrease").exists()
    assert ListingPriceHistory.objects.filter(direction="increase").exists()
