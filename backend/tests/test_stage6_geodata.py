from __future__ import annotations

from decimal import Decimal

import pytest
from asgiref.sync import async_to_sync
from django.contrib.auth import get_user_model
from django.contrib.gis.geos import Point
from rest_framework.test import APIClient

from apps.geodata.contracts import GeocodingRequest
from apps.geodata.providers import DemoGeocodingProvider
from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.models import Listing
from apps.listings.services import ingest_source
from apps.searches.models import ImportantPlace, SearchProfile

pytestmark = pytest.mark.django_db


def _client(username: str) -> tuple[APIClient, object]:
    user = get_user_model().objects.create_user(username=username, password="secret")
    client = APIClient()
    client.force_authenticate(user)
    return client, user


def _seed(count: int = 8) -> list[Listing]:
    async_to_sync(ingest_source)(
        DemoListingSourceAdapter(),
        SourceSearchRequest(limit=count, seed=606),
    )
    return list(Listing.objects.order_by("external_id"))


def test_listing_coordinates_are_synchronized_to_postgis_point():
    listing = Listing(
        latitude=Decimal("49.839700"),
        longitude=Decimal("24.029700"),
    )

    listing.sync_location()

    assert isinstance(listing.location, Point)
    assert listing.location.srid == 4326
    assert listing.location.x == pytest.approx(24.0297)
    assert listing.location.y == pytest.approx(49.8397)


def test_demo_geocoder_is_deterministic_and_ukraine_scoped():
    provider = DemoGeocodingProvider()
    request = GeocodingRequest(query="Львів, вул. Зелена 10", city="Львів")

    first = async_to_sync(provider.geocode)(request)
    second = async_to_sync(provider.geocode)(request)

    assert first == second
    assert first.country_code == "UA"
    assert 49.7 < first.latitude < 50.0
    assert 23.8 < first.longitude < 24.3
    assert first.provider == "demo"


def test_seeded_demo_listings_have_postgis_locations():
    listings = _seed(6)

    assert len(listings) == 6
    assert all(listing.location is not None for listing in listings)
    assert all(listing.location.srid == 4326 for listing in listings if listing.location)


def test_map_endpoint_returns_geojson_and_respects_bbox():
    listings = _seed(12)
    client, _ = _client("stage6-map")
    lviv = next(item for item in listings if item.city == "Львів")
    assert lviv.longitude is not None and lviv.latitude is not None
    west = float(lviv.longitude) - 0.02
    south = float(lviv.latitude) - 0.02
    east = float(lviv.longitude) + 0.02
    north = float(lviv.latitude) + 0.02

    response = client.get(
        "/api/v1/map/listings/",
        {"bbox": f"{west},{south},{east},{north}", "limit": 100},
    )

    assert response.status_code == 200
    assert response.data["type"] == "FeatureCollection"
    assert response.data["features"]
    assert all(feature["geometry"]["type"] == "Point" for feature in response.data["features"])
    assert all(feature["properties"]["city"] == "Львів" for feature in response.data["features"])


def test_map_endpoint_rejects_invalid_bbox():
    client, _ = _client("stage6-bbox")

    response = client.get("/api/v1/map/listings/", {"bbox": "30,50,20,40"})

    assert response.status_code == 400


def test_important_place_crud_geocodes_address_and_is_user_scoped():
    first_client, first_user = _client("stage6-owner")
    second_client, second_user = _client("stage6-stranger")
    profile = SearchProfile.objects.create(user=first_user, name="Львів", city="Львів")
    other_profile = SearchProfile.objects.create(user=second_user, name="Чужий", city="Львів")

    created = first_client.post(
        f"/api/v1/search-profiles/{profile.id}/important-places/",
        {
            "name": "Офіс",
            "address": "вул. Наукова 7",
            "max_distance_km": "5.00",
            "importance": 5,
        },
        format="json",
    )

    assert created.status_code == 201
    assert created.data["latitude"] is not None
    assert created.data["longitude"] is not None
    place = ImportantPlace.objects.get(pk=created.data["id"])
    assert place.location is not None

    forbidden = second_client.get(
        f"/api/v1/search-profiles/{profile.id}/important-places/"
    )
    own_empty = second_client.get(
        f"/api/v1/search-profiles/{other_profile.id}/important-places/"
    )

    assert forbidden.status_code == 404
    assert own_empty.status_code == 200
    assert own_empty.data == []


def test_geocoding_preview_does_not_persist_place():
    client, user = _client("stage6-preview")
    profile = SearchProfile.objects.create(user=user, name="Рівне", city="Рівне")

    response = client.post(
        f"/api/v1/search-profiles/{profile.id}/important-places/geocode/",
        {"address": "вул. Соборна 1"},
        format="json",
    )

    assert response.status_code == 200
    assert response.data["provider"] == "demo"
    assert ImportantPlace.objects.filter(search_profile=profile).count() == 0


def test_map_context_returns_distance_to_owned_important_place():
    listing = _seed(1)[0]
    client, user = _client("stage6-context")
    profile = SearchProfile.objects.create(user=user, name="Пошук", city=listing.city)
    ImportantPlace.objects.create(
        search_profile=profile,
        name="Точка",
        latitude=listing.latitude,
        longitude=listing.longitude,
        max_distance_km=Decimal("2.00"),
    )

    response = client.get(
        f"/api/v1/search-profiles/{profile.id}/map-context/",
        {"listing_ids": str(listing.id)},
    )

    assert response.status_code == 200
    assert len(response.data["places"]) == 1
    distance = response.data["distances"][str(listing.id)][0]["distance_km"]
    assert distance == pytest.approx(0.0, abs=0.01)
