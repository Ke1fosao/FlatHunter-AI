from __future__ import annotations

from dataclasses import asdict, dataclass
from decimal import Decimal
from typing import Any

from apps.listings.models import Listing
from apps.searches.models import SearchProfile


@dataclass(frozen=True)
class MatchComponent:
    code: str
    label: str
    score: int
    weight: int
    status: str
    explanation: str


@dataclass(frozen=True)
class MatchEvaluation:
    score: int
    eligible: bool
    summary: str
    strengths: tuple[str, ...]
    compromises: tuple[str, ...]
    unknowns: tuple[str, ...]
    components: tuple[MatchComponent, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "score": self.score,
            "eligible": self.eligible,
            "summary": self.summary,
            "strengths": list(self.strengths),
            "compromises": list(self.compromises),
            "unknowns": list(self.unknowns),
            "components": [asdict(component) for component in self.components],
        }


def _component(
    code: str,
    label: str,
    score: int,
    weight: int,
    explanation: str,
    *,
    unknown: bool = False,
) -> MatchComponent:
    status = (
        "unknown" if unknown else "strong" if score >= 80 else "partial" if score >= 45 else "miss"
    )
    return MatchComponent(code, label, max(0, min(score, 100)), weight, status, explanation)


def _price_component(profile: SearchProfile, listing: Listing) -> MatchComponent:
    minimum = profile.price_min
    maximum = profile.price_max
    price = listing.price_uah
    if minimum is None and maximum is None:
        return _component("price", "Бюджет", 70, 30, "Бюджет у пошуку не обмежено.", unknown=True)
    if minimum is not None and price < minimum:
        distance = (minimum - price) / max(minimum, 1)
        score = max(55, round(90 - distance * 100))
        return _component(
            "price", "Бюджет", score, 30, f"Ціна на {minimum - price:,} грн нижча за мінімум."
        )
    if maximum is not None and price > maximum:
        over = (price - maximum) / max(maximum, 1)
        score = max(0, round(100 - over * 220))
        return _component(
            "price", "Бюджет", score, 30, f"Перевищення бюджету: {price - maximum:,} грн."
        )
    return _component("price", "Бюджет", 100, 30, "Ціна входить у заданий діапазон.")


def _location_component(profile: SearchProfile, listing: Listing) -> MatchComponent:
    if listing.city.casefold() != profile.city.casefold():
        return _component("location", "Локація", 0, 25, "Інше місто.")
    desired = {str(value).casefold() for value in profile.desired_districts}
    excluded = {str(value).casefold() for value in profile.excluded_districts}
    district = listing.district.casefold()
    if district and district in excluded:
        return _component("location", "Локація", 0, 25, "Район виключений у профілі пошуку.")
    if desired:
        if district in desired:
            return _component("location", "Локація", 100, 25, "Квартира у бажаному районі.")
        return _component(
            "location", "Локація", 55, 25, "Місто підходить, але район не серед пріоритетних."
        )
    return _component("location", "Локація", 90, 25, "Місто повністю відповідає пошуку.")


def _rooms_component(profile: SearchProfile, listing: Listing) -> MatchComponent:
    accepted = {int(value) for value in profile.rooms if str(value).isdigit()}
    if not accepted:
        return _component("rooms", "Кімнати", 75, 15, "Кількість кімнат не обмежено.", unknown=True)
    if listing.rooms in accepted:
        return _component("rooms", "Кімнати", 100, 15, "Кількість кімнат відповідає профілю.")
    distance = min(abs(listing.rooms - room) for room in accepted)
    score = 50 if distance == 1 else 10
    return _component("rooms", "Кімнати", score, 15, "Кількість кімнат відрізняється від бажаної.")


def _property_component(profile: SearchProfile, listing: Listing) -> MatchComponent:
    accepted = {str(value).casefold() for value in profile.property_types}
    if not accepted:
        return _component("property", "Тип житла", 75, 10, "Тип житла не обмежено.", unknown=True)
    if listing.property_type.casefold() in accepted:
        return _component("property", "Тип житла", 100, 10, "Тип житла відповідає пошуку.")
    return _component("property", "Тип житла", 20, 10, "Тип житла не відповідає профілю.")


def _preferences_component(profile: SearchProfile, listing: Listing) -> MatchComponent:
    checks: list[int] = []
    notes: list[str] = []
    if profile.children:
        if listing.children_allowed is True:
            checks.append(100)
        elif listing.children_allowed is False:
            checks.append(0)
            notes.append("діти не дозволені")
        else:
            checks.append(55)
            notes.append("умови для дітей не вказані")
    pets_requested = bool(profile.pets)
    if pets_requested:
        if listing.pets_allowed is True:
            checks.append(100)
        elif listing.pets_allowed is False:
            checks.append(0)
            notes.append("тварини не дозволені")
        else:
            checks.append(55)
            notes.append("умови для тварин не вказані")
    if not checks:
        return _component(
            "preferences", "Особливі умови", 75, 10, "Додаткових обмежень немає.", unknown=True
        )
    score = round(sum(checks) / len(checks))
    explanation = (
        "Особливі умови виконані." if score == 100 else "; ".join(notes).capitalize() + "."
    )
    return _component("preferences", "Особливі умови", score, 10, explanation)


def _quality_component(listing: Listing) -> MatchComponent:
    known = [
        listing.total_area,
        listing.floor,
        listing.floors_total,
        listing.building_type,
        listing.heating_type,
    ]
    completeness = sum(value not in (None, "") for value in known) / len(known)
    score = round(45 + completeness * 55)
    return _component(
        "quality",
        "Повнота даних",
        score,
        10,
        "Оцінка залежить від повноти нормалізованих параметрів.",
    )


def evaluate_match(profile: SearchProfile, listing: Listing) -> MatchEvaluation:
    components = (
        _price_component(profile, listing),
        _location_component(profile, listing),
        _rooms_component(profile, listing),
        _property_component(profile, listing),
        _preferences_component(profile, listing),
        _quality_component(listing),
    )
    weighted = sum(Decimal(component.score * component.weight) for component in components)
    total_weight = sum(component.weight for component in components)
    score = int((weighted / Decimal(total_weight)).quantize(Decimal("1")))
    hard_miss = any(
        component.code in {"location", "price"} and component.score == 0 for component in components
    )
    eligible = not hard_miss
    strengths = tuple(
        component.explanation for component in components if component.status == "strong"
    )
    compromises = tuple(
        component.explanation for component in components if component.status in {"partial", "miss"}
    )
    unknowns = tuple(
        component.explanation for component in components if component.status == "unknown"
    )
    if score >= 85:
        summary = "Майже повна відповідність вашому пошуку."
    elif score >= 70:
        summary = "Хороший варіант із кількома компромісами."
    elif score >= 50:
        summary = "Часткова відповідність — варто уважно перевірити умови."
    else:
        summary = "Слабка відповідність заданим критеріям."
    return MatchEvaluation(score, eligible, summary, strengths, compromises, unknowns, components)
