from __future__ import annotations

from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.listings.models import Listing, ListingSource


@pytest.fixture
def api_user(db):
    return get_user_model().objects.create_user(
        username="stage9-api", password="safe-test-password"
    )


@pytest.fixture
def api_listing(db) -> Listing:
    source = ListingSource.objects.create(
        code="stage9-api",
        display_name="Stage 9 API",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )
    target = Listing.objects.create(
        source=source,
        external_id="api-target",
        source_url="https://example.invalid/api-target",
        canonical_url="https://example.invalid/api-target",
        title="API квартира",
        description="Синтетичний детальний опис квартири без передоплати та зовнішніх посилань.",
        city="Київ",
        district="Подільський",
        street="Київська",
        price=18000,
        price_uah=18000,
        rooms=1,
        total_area=Decimal("42.00"),
        floor=4,
        floors_total=10,
        published_at=timezone.now(),
        attributes={"demo": True},
    )
    for index in range(8):
        Listing.objects.create(
            source=source,
            external_id=f"api-comparable-{index}",
            source_url=f"https://example.invalid/api-comparable-{index}",
            canonical_url=f"https://example.invalid/api-comparable-{index}",
            title=f"Аналог {index}",
            description="Синтетичний аналог для ринкової статистики.",
            city="Київ",
            district="Подільський",
            street="Київська",
            price=16000 + index * 500,
            price_uah=16000 + index * 500,
            rooms=1,
            total_area=Decimal("42.00"),
            published_at=timezone.now(),
            attributes={"demo": True},
        )
    return target


def test_analysis_endpoints_require_authentication(api_listing):
    client = APIClient()

    response = client.get(f"/api/v1/listings/{api_listing.id}/market-analysis/")

    assert response.status_code in {401, 403}


@override_settings(MARKET_MIN_COMPARABLES=4)
def test_market_risk_history_and_idempotent_refresh_are_structured(api_user, api_listing):
    client = APIClient()
    client.force_login(api_user)

    market = client.get(f"/api/v1/listings/{api_listing.id}/market-analysis/")
    risk = client.get(f"/api/v1/listings/{api_listing.id}/risk-analysis/")
    history = client.get(f"/api/v1/listings/{api_listing.id}/price-history/")
    first = client.post(
        f"/api/v1/listings/{api_listing.id}/analysis/refresh/",
        {"force": False, "provider": "untrusted", "weights": {"price": 999}},
        format="json",
        HTTP_IDEMPOTENCY_KEY="stage9-same-request",
    )
    second = client.post(
        f"/api/v1/listings/{api_listing.id}/analysis/refresh/",
        {"force": False},
        format="json",
        HTTP_IDEMPOTENCY_KEY="stage9-same-request",
    )

    assert market.status_code == 200
    assert market.data["assessment"]["status"] == "ready"
    assert market.data["assessment"]["provider"] == "local"
    assert market.data["assessment"]["comparable_count"] >= 4
    assert risk.status_code == 200
    assert 0 <= risk.data["assessment"]["score"] <= 100
    assert risk.data["disclaimer"]
    assert history.status_code == 200
    assert history.data["events"] == []
    assert first.status_code == 200
    assert second.status_code == 200
    assert first.data == second.data
    assert first.data["market"]["provider"] == "local"


def test_unapproved_listing_is_not_exposed(api_user, db):
    source = ListingSource.objects.create(
        code="stage9-unapproved",
        display_name="Unapproved",
        enabled=True,
        access_mode="manual",
        legal_status="pending",
    )
    listing = Listing.objects.create(
        source=source,
        external_id="unapproved",
        source_url="https://example.invalid/unapproved",
        canonical_url="https://example.invalid/unapproved",
        title="Недоступне оголошення",
        city="Рівне",
        price=10000,
        price_uah=10000,
        rooms=1,
        published_at=timezone.now(),
    )
    client = APIClient()
    client.force_login(api_user)

    response = client.get(f"/api/v1/listings/{listing.id}/risk-analysis/")

    assert response.status_code == 404
