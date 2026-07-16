from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing
from apps.listings.services import ingest_source
from apps.matching.engine import evaluate_match
from apps.searches.models import NotificationPreference, SearchProfile


def create_profile(user, **overrides):
    values = {
        "name": "Львів до 22к",
        "city": "Львів",
        "price_min": 12000,
        "price_max": 22000,
        "rooms": [1, 2],
        "desired_districts": ["Франківський"],
        "excluded_districts": ["Сихівський"],
        "property_types": ["apartment"],
        "children": False,
        "pets": {},
    }
    values.update(overrides)
    profile = SearchProfile.objects.create(user=user, **values)
    NotificationPreference.objects.create(search_profile=profile)
    return profile


def test_match_score_is_deterministic_and_explainable(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=20, seed=43))
    user = get_user_model().objects.create_user(username="score", password="secret")
    profile = create_profile(user)
    listing = Listing.objects.filter(city="Львів").first()
    assert listing is not None

    first = evaluate_match(profile, listing)
    second = evaluate_match(profile, listing)

    assert first == second
    assert 0 <= first.score <= 100
    assert sum(component.weight for component in first.components) == 100
    assert {component.code for component in first.components} == {
        "price",
        "location",
        "rooms",
        "property",
        "preferences",
        "quality",
    }
    assert first.summary


def test_hard_location_miss_is_ineligible(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=6, seed=9))
    user = get_user_model().objects.create_user(username="location", password="secret")
    profile = create_profile(user, city="Рівне")
    listing = Listing.objects.filter(city="Київ").first()
    assert listing is not None

    evaluation = evaluate_match(profile, listing)

    assert evaluation.eligible is False
    location = next(component for component in evaluation.components if component.code == "location")
    assert location.score == 0


def test_matches_endpoint_sorts_and_filters(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=60, seed=19))
    user = get_user_model().objects.create_user(username="matches", password="secret")
    profile = create_profile(user)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(
        f"/api/v1/search-profiles/{profile.id}/matches/",
        {"min_score": 50, "ordering": "-match_score", "limit": 20},
    )

    assert response.status_code == 200
    assert response.data["meta"]["algorithm"] == "deterministic-v1"
    scores = [item["match"]["score"] for item in response.data["results"]]
    assert scores == sorted(scores, reverse=True)
    assert all(score >= 50 for score in scores)
    assert all(item["match"]["eligible"] for item in response.data["results"])
    assert all(item["match"]["components"] for item in response.data["results"])


def test_matches_endpoint_enforces_profile_ownership(db):
    owner = get_user_model().objects.create_user(username="owner", password="secret")
    stranger = get_user_model().objects.create_user(username="stranger", password="secret")
    profile = create_profile(owner)
    client = APIClient()
    client.force_authenticate(stranger)

    response = client.get(f"/api/v1/search-profiles/{profile.id}/matches/")

    assert response.status_code == 404


def test_matches_endpoint_rejects_invalid_query(db):
    user = get_user_model().objects.create_user(username="invalid", password="secret")
    profile = create_profile(user)
    client = APIClient()
    client.force_authenticate(user)

    response = client.get(f"/api/v1/search-profiles/{profile.id}/matches/", {"min_score": 101})

    assert response.status_code == 400
