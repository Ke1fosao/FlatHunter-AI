from __future__ import annotations

import re
from typing import Any

from apps.searches.parser import parse_search_text


def build_search_extraction(text: str) -> dict[str, Any]:
    parsed = parse_search_text(text)
    data = dict(parsed.data)
    confidence = dict(parsed.confidence)
    _add_important_places(text, data, confidence)
    missing_fields = [field for field in ("city", "price_max", "rooms") if field not in data]
    return {
        "data": data,
        "confidence": confidence,
        "missing_fields": missing_fields,
    }


def build_listing_summary(listing: dict[str, Any]) -> dict[str, Any]:
    price = _money(listing.get("price_uah"))
    rooms = listing.get("rooms") or "?"
    area = listing.get("total_area")
    area_text = f", {area} м²" if area else ""
    district = listing.get("district") or "район не вказано"
    city = listing.get("city") or "місто не вказано"
    floor = listing.get("floor")
    floors_total = listing.get("floors_total")
    floor_text = f"{floor}/{floors_total}" if floor and floors_total else "потрібно уточнити"

    advantages: list[str] = []
    caveats: list[str] = []
    unknowns: list[str] = []

    if listing.get("pets_allowed") is True:
        advantages.append("Можна з домашніми тваринами.")
    elif listing.get("pets_allowed") is False:
        caveats.append("Тварини вказані як небажані або заборонені.")
    else:
        unknowns.append("Умови проживання з тваринами не вказані.")

    if listing.get("children_allowed") is False:
        caveats.append("Проживання з дітьми вказане як небажане або заборонене.")
    elif listing.get("children_allowed") is None:
        unknowns.append("Умови проживання з дітьми не вказані.")

    if listing.get("commission_percent") in (None, ""):
        unknowns.append("Комісія не вказана.")
    elif float(listing["commission_percent"]) == 0:
        advantages.append("Комісія не заявлена.")
    else:
        caveats.append(f"Комісія заявлена: {listing['commission_percent']}%.")

    if listing.get("is_owner") is True:
        advantages.append("Оголошення позначене як від власника.")
    elif listing.get("is_owner") is None:
        unknowns.append("Не підтверджено, власник це чи представник.")

    if listing.get("building_type"):
        advantages.append(f"Тип будинку: {listing['building_type']}.")
    else:
        unknowns.append("Тип будинку не вказано.")

    attributes = listing.get("attributes") or {}
    if attributes.get("backup_power") is True:
        advantages.append("Заявлене резервне живлення.")
    elif attributes.get("backup_power") is None:
        unknowns.append("Немає інформації про резервне живлення.")

    summary = (
        f"{rooms}-кімнатний варіант у місті {city}, {district}, за {price}{area_text}. "
        f"Поверх: {floor_text}. Перевірте невідомі умови перед домовленістю про перегляд."
    )
    return {
        "summary": summary,
        "advantages": advantages[:8],
        "caveats": caveats[:8],
        "unknowns": unknowns[:8],
        "confidence": {
            "summary": 0.78,
            "advantages": 0.72,
            "caveats": 0.7,
            "unknowns": 0.8,
        },
    }


def build_owner_questions(
    listing: dict[str, Any], profile: dict[str, Any] | None = None
) -> dict[str, Any]:
    profile = profile or {}
    questions = [
        "Чи актуальна квартира?",
        "Ви власник чи представник?",
        "Яка комісія та розмір застави?",
        "Коли можна подивитися квартиру?",
        "Чи укладається офіційний договір?",
        "Які приблизні комунальні платежі взимку?",
    ]

    wanted_pets = [name for name, enabled in (profile.get("pets") or {}).items() if enabled]
    if wanted_pets and listing.get("pets_allowed") is not True:
        pet_names = ", ".join(_pet_label(name) for name in wanted_pets)
        questions.append(f"Чи можна проживати з домашніми тваринами ({pet_names})?")
    elif listing.get("pets_allowed") is not True:
        questions.append("Чи можна проживати з котом або собакою?")

    if profile.get("children") and listing.get("children_allowed") is not True:
        questions.append("Чи можна проживати з дитиною або дітьми?")
    if listing.get("heating_type") in (None, ""):
        questions.append("Який тип опалення?")

    attributes = listing.get("attributes") or {}
    profile_filters = profile.get("filters") or {}
    if not attributes.get("backup_power") or profile_filters.get("backup_power"):
        questions.append("Чи є резервне живлення або інвертор?")
    if profile_filters.get("parking") and not attributes.get("parking"):
        questions.append("Чи є закріплене або безпечне місце для паркування?")

    floor = listing.get("floor")
    if isinstance(floor, int) and floor > 4:
        questions.append("Чи працює ліфт під час відключень?")

    unique_questions = list(dict.fromkeys(questions))[:12]
    message_parts = unique_questions[:5]
    message = "Добрий день! " + " ".join(message_parts)
    return {
        "questions": unique_questions,
        "message": message,
        "confidence": {"questions": 0.84, "message": 0.8},
    }


def build_listing_comparison(listings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_comparison_row(item) for item in listings]
    ranked = sorted(rows, key=_comparison_rank)
    winner = ranked[0] if ranked else None
    runner_up = ranked[1] if len(ranked) > 1 else None

    recommended_listing_id: str | None = None
    is_decisive = False
    if winner and winner["match_score"] is not None:
        winner_score = int(winner["match_score"])
        runner_score = int(runner_up["match_score"]) if runner_up else 0
        score_gap = winner_score - runner_score
        is_decisive = runner_up is None or score_gap >= 5
        if is_decisive:
            recommended_listing_id = str(winner["id"])
            recommendation = (
                f"Для заданого пошукового профілю найсильніший збіг — "
                f"'{winner['title']}' із Match Score {winner_score}%. "
                "Перед рішенням перевірте заставу, комісію та всі невідомі параметри."
            )
        else:
            recommendation = (
                "Різниця між найкращими варіантами незначна, тому немає достатніх підстав "
                "називати одну квартиру однозначно найкращою. Порівняйте локацію, заставу "
                "та невідомі умови."
            )
    elif winner:
        recommendation = (
            "Без пошукового профілю система не робить персонального висновку. "
            f"Найдешевший варіант — '{winner['title']}', але ціна сама по собі не визначає "
            "якість квартири."
        )
    else:
        recommendation = "Недостатньо квартир для порівняння."

    unknowns = sorted({unknown for row in rows for unknown in row["unknowns"]})
    tradeoffs = [
        "Нижча ціна не завжди означає кращий варіант: перевірте комісію, заставу і стан ремонту.",
        (
            "Точний час у дорозі потребує routing provider; "
            "без нього система не створює фальшиву точність."
        ),
        (
            "Risk Score буде доданий окремим ринковим і ризиковим етапом; "
            "зараз він позначається як невідомий."
        ),
    ]
    return {
        "listings": rows,
        "recommended_listing_id": recommended_listing_id,
        "is_decisive": is_decisive,
        "recommendation": recommendation,
        "tradeoffs": tradeoffs,
        "unknowns": unknowns,
        "confidence": {"recommendation": 0.78 if is_decisive else 0.62, "comparison": 0.82},
    }


def _comparison_row(listing: dict[str, Any]) -> dict[str, Any]:
    unknowns: list[str] = []
    advantages: list[str] = []
    disadvantages: list[str] = []
    attributes = listing.get("attributes") or {}

    commission_percent = _optional_float(listing.get("commission_percent"))
    if commission_percent is None:
        unknowns.append("commission")
    elif commission_percent == 0:
        advantages.append("Без заявленої комісії")
    else:
        disadvantages.append(f"Комісія {commission_percent:g}%")

    if listing.get("pets_allowed") is None:
        unknowns.append("pets")
    elif listing.get("pets_allowed") is True:
        advantages.append("Можна з тваринами")
    else:
        disadvantages.append("Тварини заборонені або небажані")

    if listing.get("children_allowed") is None:
        unknowns.append("children")
    if not listing.get("heating_type"):
        unknowns.append("heating")
    if not listing.get("total_area"):
        unknowns.append("area")
    if not listing.get("renovation_level"):
        unknowns.append("renovation")
    if attributes.get("backup_power") is None:
        unknowns.append("backup_power")
    elif attributes.get("backup_power") is True:
        advantages.append("Є резервне живлення")
    if attributes.get("parking") is None:
        unknowns.append("parking")

    price_uah = int(listing.get("price_uah") or 0)
    deposit_months = _optional_float(attributes.get("deposit_months"))
    known_first_payment_uah: int | None = None
    if deposit_months is None:
        unknowns.append("deposit")
    else:
        commission_amount = int(price_uah * (commission_percent or 0) / 100)
        known_first_payment_uah = int(price_uah * (1 + deposit_months)) + commission_amount

    match_score = listing.get("match_score")
    if not isinstance(match_score, int):
        match_score = None
        unknowns.append("match_score")

    risk_score = listing.get("risk_score")
    if not isinstance(risk_score, int):
        risk_score = None
        unknowns.append("risk_score")

    travel_minutes = listing.get("travel_minutes")
    if not isinstance(travel_minutes, int):
        travel_minutes = None
        unknowns.append("travel_time")

    return {
        "id": str(listing.get("id", "")),
        "title": str(listing.get("title", "")),
        "city": str(listing.get("city", "")),
        "district": str(listing.get("district", "")),
        "price_uah": price_uah,
        "price": _money(price_uah),
        "rooms": listing.get("rooms"),
        "area": str(listing.get("total_area") or ""),
        "area_value": float(listing.get("total_area") or 0),
        "floor": _floor(listing),
        "commission": _commission(listing),
        "known_first_payment_uah": known_first_payment_uah,
        "pets": _pets(listing),
        "children_allowed": listing.get("children_allowed"),
        "building_type": str(listing.get("building_type") or ""),
        "renovation_level": str(listing.get("renovation_level") or ""),
        "heating_type": str(listing.get("heating_type") or ""),
        "backup_power": attributes.get("backup_power"),
        "parking": attributes.get("parking"),
        "match_score": match_score,
        "risk_score": risk_score,
        "travel_minutes": travel_minutes,
        "advantages": advantages,
        "disadvantages": disadvantages,
        "unknowns": sorted(set(unknowns)),
    }


def _comparison_rank(item: dict[str, Any]) -> tuple[int, int, int, float]:
    match_score = item.get("match_score")
    score_rank = -(int(match_score) if isinstance(match_score, int) else -1)
    completeness_rank = len(item.get("unknowns", []))
    return (score_rank, completeness_rank, int(item["price_uah"]), -float(item["area_value"]))


def _add_important_places(
    text: str,
    data: dict[str, Any],
    confidence: dict[str, float],
) -> None:
    normalized = " ".join(text.lower().split())
    place_name = ""
    if "політех" in normalized:
        place_name = "Львівська політехніка"
    elif "університет" in normalized:
        place_name = "університет"
    elif "робот" in normalized:
        place_name = "робота"

    if not place_name:
        return

    minutes = 30
    match = re.search(r"до\s+(\d{1,3})\s*(?:хв|хвилин)", normalized)
    if match:
        minutes = min(max(int(match.group(1)), 1), 240)

    data["important_places"] = [
        {
            "name": place_name,
            "max_transit_minutes": minutes,
            "importance": 5 if place_name == "Львівська політехніка" else 4,
        }
    ]
    confidence["important_places.0.name"] = 0.9
    confidence["important_places.0.max_transit_minutes"] = 0.86 if match else 0.55


def _money(value: Any) -> str:
    if value in (None, ""):
        return "ціну не вказано"
    return f"{int(value):,} грн".replace(",", " ")


def _floor(listing: dict[str, Any]) -> str:
    floor = listing.get("floor")
    floors_total = listing.get("floors_total")
    if floor and floors_total:
        return f"{floor}/{floors_total}"
    if floor:
        return str(floor)
    return "не вказано"


def _commission(listing: dict[str, Any]) -> str:
    value = _optional_float(listing.get("commission_percent"))
    if value is None:
        return "потрібно уточнити"
    if value == 0:
        return "без комісії"
    return f"{value:g}%"


def _pets(listing: dict[str, Any]) -> str:
    if listing.get("pets_allowed") is True:
        return "можна"
    if listing.get("pets_allowed") is False:
        return "не можна"
    return "потрібно уточнити"


def _pet_label(value: str) -> str:
    labels = {"cat": "кіт", "dog": "собака"}
    return labels.get(value, value)


def _optional_float(value: Any) -> float | None:
    if value in (None, ""):
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
