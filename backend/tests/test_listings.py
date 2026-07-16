from __future__ import annotations

from typing import Any

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.core.management import call_command
from rest_framework.test import APIClient

from apps.listings.contracts import NormalizedListingData, SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing, ListingSource, RawListing
from apps.listings.services import ingest_source


class PartiallyBrokenDemoAdapter(DemoListingSourceAdapter):
    source_code = "broken-demo"
    display_name = "Partially broken demo"

    async def normalize(self, raw_listing: dict[str, Any]) -> NormalizedListingData:
        if raw_listing["external_id"] == "demo-0002":
            raise ValueError("synthetic normalization failure")
        return await super().normalize(raw_listing)


def test_demo_adapter_is_deterministic():
    adapter = DemoListingSourceAdapter()
    first = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=42))
    second = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=42))

    assert first == second
    assert len(first) == 3
    assert first[0]["attributes"]["demo"] is True


def test_search_request_rejects_unsafe_limit():
    try:
        SourceSearchRequest(limit=0)
    except ValueError as error:
        assert "between 1 and 1000" in str(error)
    else:
        raise AssertionError("Expected invalid limit to raise ValueError")


def test_ingestion_is_idempotent(db):
    adapter = DemoListingSourceAdapter()
    request = SourceSearchRequest(limit=5, seed=7)

    first = async_to_sync(ingest_source)(adapter, request)
    second = async_to_sync(ingest_source)(adapter, request)

    assert first.created == 5
    assert first.failed == 0
    assert second.unchanged == 5
    assert second.failed == 0
    assert Listing.objects.count() == 5
    assert RawListing.objects.count() == 5


def test_ingestion_preserves_raw_payload_when_one_item_fails(db):
    result = async_to_sync(ingest_source)(
        PartiallyBrokenDemoAdapter(),
        SourceSearchRequest(limit=3, seed=11),
    )

    assert result.received == 3
    assert result.created == 2
    assert result.failed == 1
    assert Listing.objects.filter(source_id="broken-demo").count() == 2
    failed_raw = RawListing.objects.get(source_id="broken-demo", external_id="demo-0002")
    assert "synthetic normalization failure" in failed_raw.normalization_error
    assert failed_raw.normalized_at is None
    assert ListingSource.objects.get(pk="broken-demo").health_status == "degraded"


def test_seed_demo_listings_command_is_repeatable(db):
    call_command("seed_demo_listings", count=4, seed=23)
    call_command("seed_demo_listings", count=4, seed=23)

    assert Listing.objects.count() == 4
    assert RawListing.objects.count() == 4


def test_authenticated_listing_feed_supports_filters(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=30, seed=19))
    user = get_user_model().objects.create_user(username="feed", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/listings/", {"city": "Львів", "rooms": 1})

    assert response.status_code == 200
    assert response.data["count"] >= 1
    assert all(item["city"] == "Львів" for item in response.data["results"])
    assert all(item["rooms"] == 1 for item in response.data["results"])
    assert all(item["is_demo"] is True for item in response.data["results"])


def test_listing_feed_rejects_invalid_filter_values(db):
    user = get_user_model().objects.create_user(username="filters", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    invalid_rooms = client.get("/api/v1/listings/", {"rooms": "abc"})
    invalid_range = client.get(
        "/api/v1/listings/",
        {"price_min": 20000, "price_max": 10000},
    )

    assert invalid_rooms.status_code == 400
    assert invalid_range.status_code == 400


def test_listing_feed_hides_disabled_sources(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=3, seed=31))
    ListingSource.objects.filter(pk="demo").update(enabled=False)
    user = get_user_model().objects.create_user(username="disabled", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/listings/")

    assert response.status_code == 200
    assert response.data["count"] == 0


def test_listing_feed_requires_authentication(db):
    response = APIClient().get("/api/v1/listings/")
    assert response.status_code in {401, 403}
