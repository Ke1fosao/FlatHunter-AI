from __future__ import annotations

from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.searches.parser import parse_search_text


def test_natural_language_parser_extracts_supported_criteria():
    parsed = parse_search_text(
        "Шукаю однокімнатну квартиру у Львові до 18 тисяч, новобудова, не перший поверх, з котом і без комісії"
    )

    assert parsed.data["city"] == "Львів"
    assert parsed.data["rooms"] == [1]
    assert parsed.data["price_max"] == 18000
    assert parsed.data["pets"] == {"cat": True}
    assert parsed.data["filters"]["commission_allowed"] is False
    assert parsed.missing_fields == []


def test_user_can_create_and_list_only_own_search_profiles(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(username="dmytro", password="secret")
    other = user_model.objects.create_user(username="other", password="secret")
    client = APIClient()
    client.force_authenticate(user)

    response = client.post(
        "/api/v1/search-profiles/",
        {
            "name": "Квартира біля університету",
            "city": "Львів",
            "deal_type": "rent",
            "price_max": 18000,
            "currency": "UAH",
            "rooms": [1],
            "pets": {"cat": True},
            "important_places": [
                {"name": "Львівська політехніка", "max_transit_minutes": 25, "importance": 5}
            ],
            "notification_preference": {"frequency": "instant", "min_match_score": 80},
        },
        format="json",
    )
    assert response.status_code == 201

    from apps.searches.models import SearchProfile

    SearchProfile.objects.create(user=other, name="Hidden", city="Київ")
    listed = client.get("/api/v1/search-profiles/")
    assert listed.status_code == 200
    assert listed.data["count"] == 1
    assert listed.data["results"][0]["name"] == "Квартира біля університету"


def test_profile_rejects_invalid_price_range(db):
    user = get_user_model().objects.create_user(username="price", password="secret")
    client = APIClient()
    client.force_authenticate(user)
    response = client.post(
        "/api/v1/search-profiles/",
        {"name": "Invalid", "city": "Рівне", "price_min": 20000, "price_max": 10000},
        format="json",
    )
    assert response.status_code == 400
