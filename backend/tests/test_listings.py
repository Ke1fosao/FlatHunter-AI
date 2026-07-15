from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing, RawListing
from apps.listings.services import ingest_source


def test_demo_adapter_is_deterministic():
    adapter = DemoListingSourceAdapter()
    first = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=42))
    second = async_to_sync(adapter.search)(SourceSearchRequest(limit=3, seed=42))

    assert first == second
    assert len(first) == 3
    assert first[0]["attributes"]["demo"] is True


def test_ingestion_is_idempotent(db):
    adapter = DemoListingSourceAdapter()
    request = SourceSearchRequest(limit=5, seed=7)

    first = async_to_sync(ingest_source)(adapter, request)
    second = async_to_sync(ingest_source)(adapter, request)

    assert first.created == 5
    assert second.unchanged == 5
    assert Listing.objects.count() == 5
    assert RawListing.objects.count() == 5


def test_authenticated_listing_feed_supports_filters(db):
    async_to_sync(ingest_source)(
        DemoListingSourceAdapter(), SourceSearchRequest(limit=30, seed=19)
    )
    user = get_user_model().objects.create_user(username="feed", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.get("/api/v1/listings/", {"city": "Львів", "rooms": 1})

    assert response.status_code == 200
    assert response.data["count"] >= 1
    assert all(item["city"] == "Львів" for item in response.data["results"])
    assert all(item["rooms"] == 1 for item in response.data["results"])
    assert all(item["is_demo"] is True for item in response.data["results"])


def test_listing_feed_requires_authentication(db):
    response = APIClient().get("/api/v1/listings/")
    assert response.status_code in {401, 403}
