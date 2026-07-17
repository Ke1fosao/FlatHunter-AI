from __future__ import annotations

from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework.test import APIClient

from apps.ai_analysis.models import AIRequest
from apps.ai_analysis.services import parse_search_with_ai
from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing
from apps.listings.services import ingest_source


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
def test_owner_questions_endpoint_returns_questions_and_copy_text(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=3, seed=89))
    listing = Listing.objects.first()
    assert listing is not None
    user = get_user_model().objects.create_user(username="questions", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        f"/api/v1/ai/listings/{listing.id}/owner-questions/",
        {},
        format="json",
    )

    assert response.status_code == 200
    assert len(response.data["questions"]) >= 5
    assert "?" in response.data["message"]
    assert response.data["meta"]["status"] == "success"


@override_settings(AI_ENABLED=True, AI_PROVIDER="local_rules", AI_MODEL="local-rules-v1")
def test_listing_compare_endpoint_compares_two_to_five_listings(db):
    async_to_sync(ingest_source)(DemoListingSourceAdapter(), SourceSearchRequest(limit=5, seed=90))
    listing_ids = list(Listing.objects.values_list("id", flat=True)[:3])
    user = get_user_model().objects.create_user(username="compare-ai", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/ai/listings/compare/",
        {"listing_ids": [str(item) for item in listing_ids]},
        format="json",
    )

    assert response.status_code == 200
    assert len(response.data["listings"]) == 3
    assert response.data["recommendation"]
    assert response.data["meta"]["feature"] == "listings.compare"
    assert AIRequest.objects.filter(feature="listings.compare", user=user).exists()


def test_listing_compare_endpoint_validates_listing_count(db):
    user = get_user_model().objects.create_user(username="compare-count", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post("/api/v1/ai/listings/compare/", {"listing_ids": []}, format="json")

    assert response.status_code == 400
