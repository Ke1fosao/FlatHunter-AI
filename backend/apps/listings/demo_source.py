from __future__ import annotations

import random
from datetime import timedelta
from typing import Any

from django.utils import timezone

from apps.listings.contracts import (
    ListingSourceAdapter,
    NormalizedListingData,
    SourceHealth,
    SourceSearchRequest,
)


class DemoListingSourceAdapter(ListingSourceAdapter):
    source_code = "demo"
    display_name = "FlatHunter Synthetic Demo"

    cities = {
        "Львів": ["Франківський", "Шевченківський", "Галицький", "Сихівський"],
        "Рівне": ["Центр", "Північний", "Ювілейний", "Щасливе"],
        "Київ": ["Шевченківський", "Подільський", "Солом'янський", "Дарницький"],
    }
    streets = ["Зелена", "Городоцька", "Соборна", "Київська", "Наукова", "Бандери"]

    async def health_check(self) -> SourceHealth:
        return SourceHealth(healthy=True, message="Synthetic source is available")

    async def search(self, request: SourceSearchRequest) -> list[dict[str, Any]]:
        rng = random.Random(request.seed)
        now = timezone.now()
        results: list[dict[str, Any]] = []
        city_names = list(self.cities)
        for index in range(request.limit):
            city = city_names[index % len(city_names)]
            district = rng.choice(self.cities[city])
            rooms = rng.randint(1, 4)
            area = round(rng.uniform(28 + rooms * 7, 42 + rooms * 18), 1)
            base_price = {"Львів": 14500, "Рівне": 10500, "Київ": 18500}[city]
            price = max(base_price + rooms * rng.randint(1800, 3900) + rng.randint(-2500, 3500), 6000)
            floor = rng.randint(1, 14)
            floors_total = max(floor, rng.randint(5, 18))
            external_id = f"demo-{index + 1:04d}"
            results.append(
                {
                    "external_id": external_id,
                    "url": f"https://example.invalid/listings/{external_id}",
                    "title": f"{rooms}-кімнатна квартира · {district}",
                    "description": "Синтетичне demo-оголошення, яке не описує реальну квартиру.",
                    "city": city,
                    "district": district,
                    "street": rng.choice(self.streets),
                    "price": price,
                    "rooms": rooms,
                    "total_area": area,
                    "floor": floor,
                    "floors_total": floors_total,
                    "building_type": rng.choice(["new_building", "brick", "panel", "historical"]),
                    "renovation_level": rng.choice(["modern", "good", "cosmetic", "needs_repair"]),
                    "heating_type": rng.choice(["individual", "central", "electric"]),
                    "pets_allowed": rng.choice([True, False, None]),
                    "children_allowed": rng.choice([True, True, False, None]),
                    "commission_percent": rng.choice([0, 50, 100, None]),
                    "is_owner": rng.choice([True, False, None]),
                    "published_at": (now - timedelta(minutes=rng.randint(5, 14400))).isoformat(),
                    "attributes": {
                        "balcony": rng.choice([True, False]),
                        "elevator": floors_total > 5,
                        "furniture": rng.choice([True, False]),
                        "backup_power": rng.choice([True, False, None]),
                        "demo": True,
                    },
                }
            )
        return results

    async def fetch_details(self, external_id: str) -> dict[str, Any]:
        for listing in await self.search(SourceSearchRequest()):
            if listing["external_id"] == external_id:
                return listing
        raise KeyError(external_id)

    async def normalize(self, raw_listing: dict[str, Any]) -> NormalizedListingData:
        external_id = str(raw_listing["external_id"])
        url = str(raw_listing["url"])
        values = {
            "source_url": url,
            "canonical_url": url,
            "title": str(raw_listing["title"]),
            "description": str(raw_listing.get("description", "")),
            "deal_type": "rent",
            "property_type": "apartment",
            "city": str(raw_listing["city"]),
            "district": str(raw_listing.get("district", "")),
            "street": str(raw_listing.get("street", "")),
            "price": int(raw_listing["price"]),
            "price_uah": int(raw_listing["price"]),
            "currency": "UAH",
            "rooms": int(raw_listing["rooms"]),
            "total_area": raw_listing.get("total_area"),
            "floor": raw_listing.get("floor"),
            "floors_total": raw_listing.get("floors_total"),
            "building_type": str(raw_listing.get("building_type", "")),
            "renovation_level": str(raw_listing.get("renovation_level", "")),
            "heating_type": str(raw_listing.get("heating_type", "")),
            "pets_allowed": raw_listing.get("pets_allowed"),
            "children_allowed": raw_listing.get("children_allowed"),
            "commission_percent": raw_listing.get("commission_percent"),
            "is_owner": raw_listing.get("is_owner"),
            "images": [],
            "attributes": dict(raw_listing.get("attributes", {})),
            "published_at": raw_listing["published_at"],
            "is_active": True,
            "normalization_version": 1,
        }
        return NormalizedListingData(external_id=external_id, values=values)
