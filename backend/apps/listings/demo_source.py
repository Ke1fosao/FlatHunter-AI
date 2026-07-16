from __future__ import annotations

import random
from datetime import UTC, datetime, timedelta
from typing import Any

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
    city_centres = {
        "Львів": (49.839683, 24.029717),
        "Рівне": (50.619900, 26.251617),
        "Київ": (50.450100, 30.523400),
    }
    streets = ["Зелена", "Городоцька", "Соборна", "Київська", "Наукова", "Бандери"]

    async def health_check(self) -> SourceHealth:
        return SourceHealth(healthy=True, message="Synthetic source is available")

    async def search(self, request: SourceSearchRequest) -> list[dict[str, Any]]:
        reference_time = datetime(2026, 7, 16, 12, 0, tzinfo=UTC)
        results: list[dict[str, Any]] = []
        city_names = list(self.cities)
        for index in range(request.limit):
            external_id = f"demo-{index + 1:04d}"
            duplicate_slot = index % 12
            duplicate_group = (
                f"demo-duplicate-{index // 12:03d}" if duplicate_slot in {0, 1, 2} else ""
            )
            property_key = duplicate_group or external_id
            property_rng = random.Random(f"{request.seed}:{property_key}:property")
            variation_rng = random.Random(f"{request.seed}:{external_id}:variation")
            city_index = index // 12 if duplicate_group else index
            city = city_names[city_index % len(city_names)]
            district = property_rng.choice(self.cities[city])
            rooms = property_rng.randint(1, 4)
            area = round(property_rng.uniform(28 + rooms * 7, 42 + rooms * 18), 1)
            base_price = {"Львів": 14500, "Рівне": 10500, "Київ": 18500}[city]
            shared_price = max(
                base_price
                + rooms * property_rng.randint(1800, 3900)
                + property_rng.randint(-2500, 3500),
                6000,
            )
            price_variation = (-350, 0, 450)[duplicate_slot] if duplicate_group else 0
            price = max(6000, shared_price + price_variation)
            floor = property_rng.randint(1, 14)
            floors_total = max(floor, property_rng.randint(5, 18))
            centre_lat, centre_lon = self.city_centres[city]
            latitude = round(centre_lat + property_rng.uniform(-0.045, 0.045), 6)
            longitude = round(centre_lon + property_rng.uniform(-0.065, 0.065), 6)
            street = property_rng.choice(self.streets)
            title_variants = (
                f"{rooms}-кімнатна квартира · {district}",
                f"Оренда {rooms}-кімнатної квартири, {district}",
                f"Квартира на {rooms} кімнати · район {district}",
            )
            title = title_variants[duplicate_slot] if duplicate_group else title_variants[0]
            description = (
                "Синтетичне demo-оголошення, яке не описує реальну квартиру."
                if not duplicate_group
                else (
                    "Синтетична копія demo-оголошення для безпечного тестування дублікатів. "
                    f"Варіант публікації {duplicate_slot + 1}."
                )
            )
            attributes: dict[str, Any] = {
                "balcony": property_rng.choice([True, False]),
                "elevator": floors_total > 5,
                "furniture": property_rng.choice([True, False]),
                "backup_power": property_rng.choice([True, False, None]),
                "demo": True,
            }
            if duplicate_group:
                attributes["demo_duplicate_group"] = duplicate_group
                attributes["building_number"] = 10 + (index // 12)
            results.append(
                {
                    "external_id": external_id,
                    "url": f"https://example.invalid/listings/{external_id}",
                    "title": title,
                    "description": description,
                    "city": city,
                    "district": district,
                    "street": street,
                    "latitude": latitude,
                    "longitude": longitude,
                    "location_accuracy": "building",
                    "price": price,
                    "rooms": rooms,
                    "total_area": area,
                    "floor": floor,
                    "floors_total": floors_total,
                    "building_type": property_rng.choice(
                        ["new_building", "brick", "panel", "historical"]
                    ),
                    "renovation_level": property_rng.choice(
                        ["modern", "good", "cosmetic", "needs_repair"]
                    ),
                    "heating_type": property_rng.choice(["individual", "central", "electric"]),
                    "pets_allowed": property_rng.choice([True, False, None]),
                    "children_allowed": property_rng.choice([True, True, False, None]),
                    "commission_percent": property_rng.choice([0, 50, 100, None]),
                    "is_owner": property_rng.choice([True, False, None]),
                    "published_at": (
                        reference_time - timedelta(minutes=variation_rng.randint(5, 14400))
                    ).isoformat(),
                    "attributes": attributes,
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
            "latitude": raw_listing.get("latitude"),
            "longitude": raw_listing.get("longitude"),
            "location_accuracy": str(raw_listing.get("location_accuracy", "district")),
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
            "normalization_version": 3,
        }
        return NormalizedListingData(external_id=external_id, values=values)
