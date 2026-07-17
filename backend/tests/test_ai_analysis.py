from __future__ import annotations

import asyncio
from decimal import Decimal

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import override_settings
from pydantic import ValidationError
from rest_framework.test import APIClient

from apps.ai_analysis.models import AIRequest
from apps.ai_analysis.schemas import ListingSummaryResult
from apps.ai_analysis.services import parse_search_with_ai
from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing
from apps.listings.services import ingest_source
from apps.searches.models import SearchProfile


class CountingSearchProvider:
    provider_name = "counting"
    model_name = "counting-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def structured_completion(self, task, schema, context):
        self.calls += 1
        return schema.model_validate(
            {
                "data": {
                    "deal_type": "rent",
                    "currency": "UAH",
                    "city": "Львів",
                    "rooms": [1],
                    "price_max": 18000,
                    "filters": {},
                },
                "confidence": {"city": 0.98, "rooms": 0.97, "price_max": 0.96},
                "missing_fields": [],
            }
        )


class SlowSearchProvider(CountingSearchProvider):
    provider_name = "slow"
    model_name = "slow-v1"

    async def structured_completion(self, task, schema, context):
        self.calls += 1
        await asyncio.sleep(0.05)
        return await super().structured_completion(task, schema, context)


class BrokenSearchProvider:
    provider_name = "broken"
    model_name = "broken-v1"

    def __init__(self) -> None:
        self.calls = 0

    async def structured_completion(self, task, schema, context):
        self.calls += 1
        raise RuntimeError("provider transport exploded")


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_local_ai_provider_extracts_structured_search_with_metadata(db):
    result = parse_search_with_ai(
        "Шукаю однокімнатну квартиру у Львові до 18 тисяч, новобудова, "
        "не перший поверх, до 25 хвилин від політехніки, з котом і без комісії."
    )

    assert result.data["city"] == "Львів"
    assert result.data["rooms"] == [1]
    assert result.data["price_max"] == 18000
    assert result.data["pets"] == {"cat": True}
    assert result.data["filters"]["building_type"] == ["new_building"]
    assert result.data["filters"]["commission_allowed"] is False
    assert result.data["important_places"] == [
        {
            "name": "Львівська політехніка",
            "max_transit_minutes": 25,
            "importance": 5,
        }
    ]
    assert result.missing_fields == []
    assert result.meta["provider"] == "local_rules"
    assert result.meta["model"] == "local-rules-v1"
    assert result.meta["status"] == "success"


@override_settings(AI_ENABLED=False, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_ai_disabled_uses_deterministic_parser_without_audit_record(db):
    result = parse_search_with_ai("Шукаю двокімнатну квартиру у Києві до 25000 грн.")

    assert result.data["city"] == "Київ"
    assert result.data["rooms"] == [2]
    assert result.data["price_max"] == 25000
    assert result.meta["status"] == "disabled"
    assert AIRequest.objects.count() == 0


@override_settings(AI_ENABLED=False, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_ai_disabled_keeps_important_place_extraction(db):
    result = parse_search_with_ai(
        "Шукаю однокімнатну квартиру у Львові до 18 тисяч, до 25 хвилин від політехніки."
    )

    assert result.data["important_places"] == [
        {
            "name": "Львівська політехніка",
            "max_transit_minutes": 25,
            "importance": 5,
        }
    ]
    assert result.confidence["important_places.0.max_transit_minutes"] == 0.86


@override_settings(AI_ENABLED=True, AI_PROVIDER="not_configured", AI_MODEL="remote-model")
def test_unconfigured_ai_provider_falls_back_to_deterministic_parser(db):
    result = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    assert result.data["city"] == "Львів"
    assert result.data["rooms"] == [1]
    assert result.data["price_max"] == 18000
    assert result.meta["status"] == "fallback"

    audit = AIRequest.objects.get()
    assert audit.status == "fallback"
    assert audit.provider == "not_configured"
    assert audit.error_message


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="slow",
    AI_MODEL="slow-v1",
    AI_TIMEOUT_SECONDS=0.01,
    AI_MAX_RETRIES=0,
    AI_CACHE_SECONDS=0,
)
def test_provider_timeout_falls_back_and_is_audited(db, monkeypatch):
    provider = SlowSearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)

    result = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    assert result.meta["status"] == "fallback"
    assert provider.calls == 1
    audit = AIRequest.objects.get()
    assert audit.status == "fallback"
    assert "timeout" in audit.error_message.lower()


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="broken",
    AI_MODEL="broken-v1",
    AI_MAX_RETRIES=0,
    AI_CIRCUIT_BREAKER_FAILURES=1,
    AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS=60,
    AI_CACHE_SECONDS=0,
)
def test_unexpected_provider_error_falls_back_and_opens_circuit(db, monkeypatch):
    cache.clear()
    provider = BrokenSearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)

    first = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")
    second = parse_search_with_ai("Шукаю двокімнатну квартиру у Києві до 25000 грн.")

    assert first.meta["status"] == "fallback"
    assert second.meta["status"] == "fallback"
    assert provider.calls == 1
    assert AIRequest.objects.filter(status="fallback").count() == 2


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="counting",
    AI_MODEL="counting-v1",
    AI_CACHE_SECONDS=60,
    AI_MAX_RETRIES=0,
)
def test_successful_ai_result_is_validated_and_cached(db, monkeypatch):
    cache.clear()
    provider = CountingSearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)

    first = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")
    second = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    assert first.meta["status"] == "success"
    assert second.meta["status"] == "cached"
    assert provider.calls == 1
    assert AIRequest.objects.exclude(cache_key="").count() == 2


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="counting",
    AI_MODEL="counting-v1",
    AI_DAILY_BUDGET=0.5,
    AI_CACHE_SECONDS=0,
)
def test_daily_budget_guard_falls_back_without_calling_provider(db, monkeypatch):
    provider = CountingSearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)
    AIRequest.objects.create(
        feature="listing.summary",
        provider="remote",
        model="remote-v1",
        prompt_version="v1",
        status="success",
        input_summary="sha256:test;chars:4",
        estimated_cost_usd=Decimal("0.750000"),
    )

    result = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    assert result.meta["status"] == "fallback"
    assert result.meta["reason"] == "daily_budget_exhausted"
    assert provider.calls == 0


def test_structured_ai_schema_rejects_invalid_confidence():
    with pytest.raises(ValidationError):
        ListingSummaryResult.model_validate(
            {
                "summary": "Коротке резюме",
                "advantages": [],
                "caveats": [],
                "unknowns": [],
                "confidence": {"summary": 1.5},
            }
        )


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_parse_endpoint_returns_ai_meta_and_writes_sanitized_audit_record(db):
    user = get_user_model().objects.create_user(username="ai-user", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/search-profiles/parse-natural-language/",
        {"text": "Шукаю однокімнатну квартиру у Львові до 18 тисяч, до 25 хвилин від політехніки."},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["data"]["city"] == "Львів"
    assert response.data["data"]["important_places"][0]["name"] == "Львівська політехніка"
    assert response.data["meta"]["provider"] == "local_rules"

    audit = AIRequest.objects.get()
    assert audit.user == user
    assert audit.feature == "search.parse_natural_language"
    assert audit.provider == "local_rules"
    assert audit.status == "success"
    assert "політехніки" not in audit.input_summary.lower()
    assert audit.output_data["data"]["city"] == "Львів"


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_listing_summary_endpoint_returns_structured_ai_result(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=3, seed=88))
    listing = Listing.objects.first()
    assert listing is not None
    user = get_user_model().objects.create_user(username="summary", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(f"/api/v1/ai/listings/{listing.id}/summary/", {}, format="json")

    assert response.status_code == 200
    assert response.data["summary"]
    assert response.data["advantages"]
    assert response.data["meta"]["provider"] == "local_rules"
    assert AIRequest.objects.filter(feature="listing.summary", user=user).exists()


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_owner_questions_endpoint_uses_owned_search_profile(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=3, seed=89))
    listing = Listing.objects.first()
    assert listing is not None
    listing.children_allowed = False
    listing.save(update_fields=("children_allowed",))
    user = get_user_model().objects.create_user(username="questions", password="secret")
    profile = SearchProfile.objects.create(
        user=user,
        name="Для сім'ї",
        city=listing.city,
        rooms=[listing.rooms],
        children=True,
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/ai/listings/{listing.id}/owner-questions/",
        {"search_profile_id": str(profile.id)},
        format="json",
    )

    assert response.status_code == 200
    assert any("дит" in question.lower() for question in response.data["questions"])
    assert "?" in response.data["message"]
    assert response.data["meta"]["status"] in {"success", "cached"}


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_listing_compare_endpoint_uses_owned_profile_and_match_score(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=5, seed=90))
    listings = list(Listing.objects.all()[:2])
    assert len(listings) == 2
    cheaper, better = listings
    cheaper.city = "Київ"
    cheaper.rooms = 3
    cheaper.price_uah = 10000
    cheaper.price = 10000
    cheaper.pets_allowed = False
    cheaper.save(update_fields=("city", "rooms", "price_uah", "price", "pets_allowed"))
    better.city = "Львів"
    better.rooms = 1
    better.price_uah = 12000
    better.price = 12000
    better.pets_allowed = True
    better.save(update_fields=("city", "rooms", "price_uah", "price", "pets_allowed"))

    user = get_user_model().objects.create_user(username="compare-ai", password="secret")
    profile = SearchProfile.objects.create(
        user=user,
        name="Мій пошук",
        city="Львів",
        price_max=15000,
        rooms=[1],
        pets={"cat": True},
    )
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/ai/listings/compare/",
        {
            "listing_ids": [str(cheaper.id), str(better.id)],
            "search_profile_id": str(profile.id),
        },
        format="json",
    )

    assert response.status_code == 200
    assert len(response.data["listings"]) == 2
    assert response.data["recommended_listing_id"] == str(better.id)
    assert response.data["is_decisive"] is True
    assert response.data["listings"][1]["match_score"] > response.data["listings"][0]["match_score"]
    assert AIRequest.objects.filter(feature="listings.compare", user=user).exists()


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_listing_compare_rejects_foreign_search_profile(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=3, seed=91))
    listing_ids = list(Listing.objects.values_list("id", flat=True)[:2])
    user = get_user_model().objects.create_user(username="profile-owner", password="secret")
    other = get_user_model().objects.create_user(username="other-profile-owner", password="secret")
    foreign_profile = SearchProfile.objects.create(user=other, name="Чужий", city="Львів")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/ai/listings/compare/",
        {
            "listing_ids": [str(item) for item in listing_ids],
            "search_profile_id": str(foreign_profile.id),
        },
        format="json",
    )

    assert response.status_code == 404


def test_listing_compare_endpoint_validates_listing_count(db):
    user = get_user_model().objects.create_user(username="compare-count", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post("/api/v1/ai/listings/compare/", {"listing_ids": []}, format="json")

    assert response.status_code == 400
