from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

CITY_ALIASES = {
    "львів": "Львів",
    "львові": "Львів",
    "рівне": "Рівне",
    "рівному": "Рівне",
    "київ": "Київ",
    "києві": "Київ",
}


@dataclass(frozen=True)
class ParsedSearch:
    data: dict[str, Any]
    confidence: dict[str, float]
    missing_fields: list[str]


def parse_search_text(text: str) -> ParsedSearch:
    normalized = " ".join(text.lower().split())
    data: dict[str, Any] = {"deal_type": "rent", "currency": "UAH", "filters": {}}
    confidence: dict[str, float] = {"deal_type": 0.95, "currency": 0.9}

    for alias, city in CITY_ALIASES.items():
        if alias in normalized:
            data["city"] = city
            confidence["city"] = 0.98
            break

    room_match = re.search(r"(\d+)\s*[- ]?(?:кімнат|кімнати|кімнатну|кімнатна)", normalized)
    if room_match:
        data["rooms"] = [int(room_match.group(1))]
        confidence["rooms"] = 0.97
    elif "однокімнат" in normalized:
        data["rooms"] = [1]
        confidence["rooms"] = 0.98
    elif "двокімнат" in normalized:
        data["rooms"] = [2]
        confidence["rooms"] = 0.98

    price_match = re.search(r"(?:до|max(?:imum)?\s*)\s?(\d{2,3})(?:\s?тисяч|\s?тис)", normalized)
    if price_match:
        data["price_max"] = int(price_match.group(1)) * 1000
        confidence["price_max"] = 0.96
    else:
        raw_price = re.search(r"(?:до|max(?:imum)?\s*)\s?(\d{4,6})", normalized)
        if raw_price:
            data["price_max"] = int(raw_price.group(1))
            confidence["price_max"] = 0.92

    filters: dict[str, Any] = data["filters"]
    if "не перший" in normalized:
        filters["exclude_first_floor"] = True
        confidence["filters.exclude_first_floor"] = 0.99
    if "не останній" in normalized:
        filters["exclude_last_floor"] = True
        confidence["filters.exclude_last_floor"] = 0.99
    if "новобуд" in normalized:
        filters["building_type"] = ["new_building"]
        confidence["filters.building_type"] = 0.95
    if "без коміс" in normalized or "комісію платити не хочу" in normalized:
        filters["commission_allowed"] = False
        confidence["filters.commission_allowed"] = 0.98
    if "кіт" in normalized or "кот" in normalized:
        data["pets"] = {"cat": True}
        confidence["pets.cat"] = 0.97
    if "собак" in normalized or "пес" in normalized:
        pets: dict[str, bool] = dict(data.get("pets", {}))
        pets["dog"] = True
        data["pets"] = pets
        confidence["pets.dog"] = 0.97

    missing_fields = [field for field in ("city", "price_max", "rooms") if field not in data]
    return ParsedSearch(data=data, confidence=confidence, missing_fields=missing_fields)
