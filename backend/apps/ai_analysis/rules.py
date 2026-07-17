from __future__ import annotations

from typing import Any


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

    summary = (
        f"{rooms}-кімнатний варіант у місті {city}, {district}, за {price}{area_text}. "
        f"Поверх: {floor_text}. Перевірте невідомі умови перед домовленістю про перегляд."
    )
    return {
        "summary": summary,
        "advantages": advantages[:6],
        "caveats": caveats[:6],
        "unknowns": unknowns[:6],
        "confidence": {
            "summary": 0.78,
            "advantages": 0.72,
            "caveats": 0.7,
            "unknowns": 0.8,
        },
    }


def build_owner_questions(listing: dict[str, Any]) -> dict[str, Any]:
    questions = [
        "Чи актуальна квартира?",
        "Ви власник чи представник?",
        "Яка комісія та розмір застави?",
        "Коли можна подивитися квартиру?",
        "Чи укладається офіційний договір?",
        "Які приблизні комунальні платежі взимку?",
    ]
    if listing.get("pets_allowed") is not True:
        questions.append("Чи можна проживати з котом або собакою?")
    if listing.get("heating_type") in (None, ""):
        questions.append("Який тип опалення?")
    if not listing.get("attributes", {}).get("backup_power"):
        questions.append("Чи є резервне живлення або інвертор?")
    floor = listing.get("floor")
    if isinstance(floor, int) and floor > 4:
        questions.append("Чи працює ліфт під час відключень?")

    message = (
        "Добрий день! Підкажіть, будь ласка, чи актуальна квартира? "
        "Яка комісія та застава? Чи можна проживати з тваринами? "
        "Також цікавлять комунальні платежі взимку та умови договору."
    )
    return {
        "questions": questions[:12],
        "message": message,
        "confidence": {"questions": 0.82, "message": 0.78},
    }


def build_listing_comparison(listings: list[dict[str, Any]]) -> dict[str, Any]:
    rows = [_comparison_row(item) for item in listings]
    ranked = sorted(rows, key=lambda item: (item["price_uah"], -item["area_value"]))
    winner = ranked[0] if ranked else None
    recommendation = (
        f"Найпрактичніше почати з варіанту '{winner['title']}', бо він має найнижчу ціну "
        "серед обраних. Якщо різниця в локації або стані ремонту важливіша за бюджет, "
        "порівняйте невідомі параметри перед рішенням."
        if winner
        else "Недостатньо квартир для порівняння."
    )
    unknowns = sorted({unknown for row in rows for unknown in row["unknowns"]})
    tradeoffs = [
        "Нижча ціна не завжди означає кращий варіант: перевірте комісію, заставу і стан ремонту.",
        "Якщо дорога до важливих місць критична, потрібен routing provider для точного часу.",
    ]
    return {
        "listings": rows,
        "recommendation": recommendation,
        "tradeoffs": tradeoffs,
        "unknowns": unknowns,
        "confidence": {"recommendation": 0.68, "comparison": 0.74},
    }


def _comparison_row(listing: dict[str, Any]) -> dict[str, Any]:
    unknowns: list[str] = []
    if listing.get("commission_percent") in (None, ""):
        unknowns.append("commission")
    if listing.get("pets_allowed") is None:
        unknowns.append("pets")
    if not listing.get("heating_type"):
        unknowns.append("heating")
    if not listing.get("total_area"):
        unknowns.append("area")
    return {
        "id": str(listing.get("id", "")),
        "title": listing.get("title", ""),
        "city": listing.get("city", ""),
        "district": listing.get("district", ""),
        "price_uah": int(listing.get("price_uah") or 0),
        "price": _money(listing.get("price_uah")),
        "rooms": listing.get("rooms"),
        "area": str(listing.get("total_area") or ""),
        "area_value": float(listing.get("total_area") or 0),
        "floor": _floor(listing),
        "commission": _commission(listing),
        "pets": _pets(listing),
        "unknowns": unknowns,
    }


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
    value = listing.get("commission_percent")
    if value in (None, ""):
        return "потрібно уточнити"
    if float(value) == 0:
        return "без комісії"
    return f"{value}%"


def _pets(listing: dict[str, Any]) -> str:
    if listing.get("pets_allowed") is True:
        return "можна"
    if listing.get("pets_allowed") is False:
        return "не можна"
    return "потрібно уточнити"
