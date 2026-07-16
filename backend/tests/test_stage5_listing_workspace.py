from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing, UserListingState
from apps.listings.services import ingest_source


def _client(username: str) -> tuple[APIClient, object]:
    user = get_user_model().objects.create_user(username=username, password="secret")
    client = APIClient()
    client.force_authenticate(user)
    return client, user


def _seed(count: int = 6) -> list[Listing]:
    async_to_sync(ingest_source)(
        DemoListingSourceAdapter(),
        SourceSearchRequest(limit=count, seed=505),
    )
    return list(Listing.objects.order_by("external_id"))


def test_favorite_state_is_persistent_and_user_scoped(db):
    listing = _seed(1)[0]
    first, first_user = _client("stage5-first")
    second, _ = _client("stage5-second")

    response = first.post(f"/api/v1/listings/{listing.id}/favorite/", {"value": True}, format="json")

    assert response.status_code == 200
    assert response.data["user_state"]["is_favorite"] is True
    assert UserListingState.objects.get(user=first_user, listing=listing).is_favorite is True
    assert first.get("/api/v1/listings/", {"favorites": "true"}).data["count"] == 1
    assert second.get("/api/v1/listings/", {"favorites": "true"}).data["count"] == 0


def test_hidden_listing_is_removed_from_feed_but_can_be_restored(db):
    listing = _seed(1)[0]
    client, _ = _client("stage5-hidden")

    hidden = client.post(f"/api/v1/listings/{listing.id}/hide/", {"value": True}, format="json")
    feed = client.get("/api/v1/listings/")
    detail = client.get(f"/api/v1/listings/{listing.id}/")
    restored = client.post(f"/api/v1/listings/{listing.id}/hide/", {"value": False}, format="json")

    assert hidden.status_code == 200
    assert feed.data["count"] == 0
    assert detail.status_code == 200
    assert detail.data["user_state"]["is_hidden"] is True
    assert restored.status_code == 200
    assert restored.data["user_state"]["is_hidden"] is False


def test_comparison_is_limited_to_four_listings(db):
    listings = _seed(5)
    client, _ = _client("stage5-compare")

    for listing in listings[:4]:
        response = client.post(
            f"/api/v1/listings/{listing.id}/compare/",
            {"value": True},
            format="json",
        )
        assert response.status_code == 200

    overflow = client.post(
        f"/api/v1/listings/{listings[4].id}/compare/",
        {"value": True},
        format="json",
    )

    assert overflow.status_code == 409
    assert overflow.data["error"]["code"] == "comparison_limit"
    assert client.get("/api/v1/listings/", {"compared": "true"}).data["count"] == 4


def test_dashboard_returns_personal_counts_and_recent_listings(db):
    listings = _seed(3)
    client, _ = _client("stage5-dashboard")
    client.post(f"/api/v1/listings/{listings[0].id}/favorite/", {"value": True}, format="json")
    client.post(f"/api/v1/listings/{listings[1].id}/compare/", {"value": True}, format="json")

    response = client.get("/api/v1/listings/dashboard/")

    assert response.status_code == 200
    assert response.data["stats"]["favorites"] == 1
    assert response.data["stats"]["compared"] == 1
    assert response.data["stats"]["available_listings"] == 3
    assert len(response.data["recent"]) == 3


def test_state_mutation_requires_boolean_value(db):
    listing = _seed(1)[0]
    client, _ = _client("stage5-validation")

    response = client.post(f"/api/v1/listings/{listing.id}/favorite/", {}, format="json")

    assert response.status_code == 400
