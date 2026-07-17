from __future__ import annotations

from decimal import Decimal
from io import StringIO

import pytest
from django.core.management import call_command
from django.utils import timezone

from apps.analysis.models import ListingSnapshot
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def command_listings(db) -> list[Listing]:
    source = ListingSource.objects.create(
        code="stage9-commands",
        display_name="Stage 9 Commands",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    return [
        Listing.objects.create(
            source=source,
            external_id=f"stage9-command-{index}",
            source_url=f"https://example.invalid/stage9-command-{index}",
            canonical_url=f"https://example.invalid/stage9-command-{index}",
            title=f"Command listing {index}",
            description="Synthetic listing for bounded Stage 9 command tests.",
            city="Львів",
            district="Франківський",
            street="Наукова",
            price=15000 + index * 500,
            price_uah=15000 + index * 500,
            rooms=1,
            total_area=Decimal("40.00"),
            published_at=timezone.now(),
            attributes={"demo": True},
        )
        for index in range(4)
    ]


def test_snapshot_backfill_dry_run_does_not_write(command_listings: list[Listing]):
    output = StringIO()

    call_command("backfill_listing_snapshots", "--dry-run", "--limit", "2", stdout=output)

    assert ListingSnapshot.objects.count() == 0
    assert "dry-run" in output.getvalue()
    assert "eligible=2" in output.getvalue()


def test_snapshot_backfill_respects_limit_and_is_idempotent(command_listings: list[Listing]):
    call_command("backfill_listing_snapshots", "--limit", "2")
    call_command("backfill_listing_snapshots", "--limit", "2")

    assert ListingSnapshot.objects.count() == 2
