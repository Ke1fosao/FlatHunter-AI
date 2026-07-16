from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from django.conf import settings

from apps.duplicates.models import CandidateDecision, ListingFingerprint
from apps.duplicates.normalization import hamming_distance64, haversine_metres, text_similarity
from apps.listings.models import Listing

ALGORITHM_VERSION = 1
_COMPONENT_WEIGHTS = {
    "exact": Decimal("25"),
    "location": Decimal("25"),
    "attributes": Decimal("15"),
    "text": Decimal("15"),
    "image": Decimal("15"),
    "price": Decimal("5"),
}


@dataclass(frozen=True)
class DuplicateEvaluation:
    exact_score: float | None
    address_score: float | None
    geo_score: float | None
    attributes_score: float | None
    text_score: float | None
    image_score: float | None
    price_score: float | None
    final_score: float
    decision: str
    reasons: tuple[dict[str, Any], ...]
    hard_conflicts: tuple[str, ...]
    exact_rule: bool

    def candidate_defaults(self) -> dict[str, Any]:
        return {
            "exact_score": self.exact_score,
            "address_score": self.address_score,
            "geo_score": self.geo_score,
            "attributes_score": self.attributes_score,
            "text_score": self.text_score,
            "image_score": self.image_score,
            "price_score": self.price_score,
            "final_score": self.final_score,
            "decision": self.decision,
            "reasons": list(self.reasons),
            "hard_conflicts": list(self.hard_conflicts),
            "algorithm_version": ALGORITHM_VERSION,
        }


def _reason(component: str, score: float | None, message: str, *, evidence: str = "") -> dict[str, Any]:
    payload: dict[str, Any] = {"component": component, "score": score, "message": message}
    if evidence:
        payload["evidence"] = evidence
    return payload


def _exact_component(
    left: Listing,
    right: Listing,
    left_fp: ListingFingerprint,
    right_fp: ListingFingerprint,
) -> tuple[float | None, list[dict[str, Any]], bool]:
    reasons: list[dict[str, Any]] = []
    exact_rule = False
    scores: list[float] = []
    if left_fp.normalized_url and left_fp.normalized_url == right_fp.normalized_url:
        scores.append(100.0)
        exact_rule = True
        reasons.append(_reason("exact", 100.0, "Однакова канонічна URL-адреса."))
    shared_contacts = set(left_fp.contact_hashes) & set(right_fp.contact_hashes)
    if shared_contacts:
        scores.append(100.0)
        reasons.append(_reason("exact", 100.0, "Збіг захешованого контакту."))
    left_exact = {item.get("exact") for item in left_fp.image_hashes if isinstance(item, dict)} - {None}
    right_exact = {item.get("exact") for item in right_fp.image_hashes if isinstance(item, dict)} - {None}
    shared_images = left_exact & right_exact
    if len(shared_images) >= 2:
        scores.append(100.0)
        exact_rule = True
        reasons.append(_reason("exact", 100.0, "Збіг щонайменше двох точних image hashes."))
    elif len(shared_images) == 1:
        scores.append(88.0)
        reasons.append(_reason("exact", 88.0, "Збіг одного точного image hash."))
    if left.source_id == right.source_id and left.external_id == right.external_id:
        scores.append(100.0)
        exact_rule = True
        reasons.append(_reason("exact", 100.0, "Однаковий ідентифікатор у джерелі."))
    return (max(scores) if scores else None), reasons, exact_rule


def _location_components(
    left: Listing,
    right: Listing,
    left_fp: ListingFingerprint,
    right_fp: ListingFingerprint,
) -> tuple[float | None, float | None, list[dict[str, Any]]]:
    reasons: list[dict[str, Any]] = []
    address: float | None = None
    if left_fp.address_key and left_fp.address_key == right_fp.address_key:
        address = 100.0
        reasons.append(_reason("address", address, "Однаковий нормалізований адресний ключ."))
    elif left_fp.normalized_street and left_fp.normalized_street == right_fp.normalized_street:
        address = 82.0
        reasons.append(_reason("address", address, "Однакова вулиця; номер будинку неповний або різниться."))
    elif left_fp.normalized_district and left_fp.normalized_district == right_fp.normalized_district:
        address = 55.0
        reasons.append(_reason("address", address, "Однаковий район, але точна адреса не підтверджена."))

    distance = haversine_metres(left, right)
    geo: float | None = None
    if distance is not None:
        if distance <= 50:
            geo = 100.0
        elif distance <= 150:
            geo = 92.0
        elif distance <= 400:
            geo = 72.0
        elif distance <= 1000:
            geo = 42.0
        else:
            geo = 0.0
        reasons.append(_reason("geo", geo, f"Відстань між координатами: {round(distance)} м."))
    return address, geo, reasons


def _attributes_component(left: Listing, right: Listing) -> tuple[float | None, list[dict[str, Any]]]:
    values: list[float] = []
    messages: list[str] = []
    if left.rooms == right.rooms:
        values.append(100.0)
        messages.append("кімнати збігаються")
    elif abs(left.rooms - right.rooms) == 1:
        values.append(45.0)
        messages.append("кількість кімнат відрізняється на одну")

    if left.total_area is not None and right.total_area is not None:
        maximum = max(float(left.total_area), float(right.total_area), 1.0)
        difference = abs(float(left.total_area) - float(right.total_area)) / maximum
        if difference <= 0.05:
            values.append(100.0)
        elif difference <= 0.12:
            values.append(82.0)
        elif difference <= 0.25:
            values.append(45.0)
        else:
            values.append(5.0)
        messages.append(f"різниця площі {round(difference * 100)}%")

    for label, left_value, right_value in (
        ("поверх", left.floor, right.floor),
        ("поверховість", left.floors_total, right.floors_total),
        ("тип будинку", left.building_type, right.building_type),
        ("ремонт", left.renovation_level, right.renovation_level),
        ("опалення", left.heating_type, right.heating_type),
    ):
        if left_value in (None, "") or right_value in (None, ""):
            continue
        values.append(100.0 if left_value == right_value else 35.0)
        messages.append(f"{label}: {'збіг' if left_value == right_value else 'відмінність'}")

    if not values:
        return None, []
    score = round(sum(values) / len(values), 2)
    return score, [_reason("attributes", score, "; ".join(messages).capitalize() + ".")]


def _image_component(
    left_fp: ListingFingerprint,
    right_fp: ListingFingerprint,
) -> tuple[float | None, list[dict[str, Any]]]:
    if not left_fp.image_hashes or not right_fp.image_hashes:
        return None, []
    left_exact = {item.get("exact") for item in left_fp.image_hashes if isinstance(item, dict)} - {None}
    right_exact = {item.get("exact") for item in right_fp.image_hashes if isinstance(item, dict)} - {None}
    exact_matches = left_exact & right_exact
    if exact_matches:
        score = 100.0 if len(exact_matches) >= 2 else 92.0
        return score, [_reason("image", score, f"Точних збігів зображень: {len(exact_matches)}.")]

    left_perceptual = [
        str(item["perceptual"])
        for item in left_fp.image_hashes
        if isinstance(item, dict) and item.get("perceptual")
    ]
    right_perceptual = [
        str(item["perceptual"])
        for item in right_fp.image_hashes
        if isinstance(item, dict) and item.get("perceptual")
    ]
    if not left_perceptual or not right_perceptual:
        return 0.0, [_reason("image", 0.0, "Image metadata є, але точних збігів не знайдено.")]
    minimum = min(
        hamming_distance64(left_hash, right_hash)
        for left_hash in left_perceptual
        for right_hash in right_perceptual
    )
    if minimum <= 4:
        score = 94.0
    elif minimum <= 8:
        score = 78.0
    elif minimum <= 14:
        score = 52.0
    else:
        score = 8.0
    return score, [_reason("image", score, f"Мінімальна Hamming-відстань perceptual hash: {minimum}.")]


def _price_component(left: Listing, right: Listing) -> tuple[float | None, list[dict[str, Any]]]:
    maximum = max(left.price_uah, right.price_uah, 1)
    difference = abs(left.price_uah - right.price_uah) / maximum
    if difference <= 0.03:
        score = 100.0
    elif difference <= 0.10:
        score = 90.0
    elif difference <= 0.20:
        score = 70.0
    elif difference <= 0.35:
        score = 40.0
    else:
        score = 12.0
    return score, [_reason("price", score, f"Різниця ціни: {round(difference * 100)}%.")]


def _hard_conflicts(left: Listing, right: Listing, distance: float | None) -> list[str]:
    conflicts: list[str] = []
    if left.deal_type.casefold() != right.deal_type.casefold():
        conflicts.append("different_deal_type")
    if left.property_type.casefold() != right.property_type.casefold():
        conflicts.append("different_property_type")
    if left.city.casefold() != right.city.casefold():
        conflicts.append("different_city")
    if abs(left.rooms - right.rooms) > 1:
        conflicts.append("incompatible_rooms")
    if left.total_area is not None and right.total_area is not None:
        maximum = max(float(left.total_area), float(right.total_area), 1.0)
        if abs(float(left.total_area) - float(right.total_area)) / maximum > 0.45:
            conflicts.append("incompatible_area")
    building_accurate = left.location_accuracy == "building" and right.location_accuracy == "building"
    if building_accurate and distance is not None and distance > 750:
        conflicts.append("incompatible_building_coordinates")
    return conflicts


def _location_score(address: float | None, geo: float | None) -> float | None:
    available = [score for score in (address, geo) if score is not None]
    return round(sum(available) / len(available), 2) if available else None


def _weighted_score(components: dict[str, float | None]) -> float:
    available = {key: value for key, value in components.items() if value is not None}
    if not available:
        return 0.0
    weighted = sum(Decimal(str(value)) * _COMPONENT_WEIGHTS[key] for key, value in available.items())
    total_weight = sum(_COMPONENT_WEIGHTS[key] for key in available)
    return float((weighted / total_weight).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))


def evaluate_duplicate(
    left: Listing,
    right: Listing,
    left_fp: ListingFingerprint,
    right_fp: ListingFingerprint,
) -> DuplicateEvaluation:
    exact, exact_reasons, exact_rule = _exact_component(left, right, left_fp, right_fp)
    address, geo, location_reasons = _location_components(left, right, left_fp, right_fp)
    attributes, attribute_reasons = _attributes_component(left, right)
    combined_left = f"{left_fp.normalized_title} {left_fp.normalized_description}".strip()
    combined_right = f"{right_fp.normalized_title} {right_fp.normalized_description}".strip()
    text = (
        text_similarity(combined_left, combined_right, left_fp.text_simhash, right_fp.text_simhash)
        if combined_left and combined_right
        else None
    )
    text_reasons = (
        [_reason("text", text, "Схожість нормалізованого заголовка й опису.")]
        if text is not None
        else []
    )
    image, image_reasons = _image_component(left_fp, right_fp)
    price, price_reasons = _price_component(left, right)
    distance = haversine_metres(left, right)
    conflicts = _hard_conflicts(left, right, distance)
    location = _location_score(address, geo)
    final = _weighted_score(
        {
            "exact": exact,
            "location": location,
            "attributes": attributes,
            "text": text,
            "image": image,
            "price": price,
        }
    )

    auto_threshold = float(settings.DUPLICATE_AUTO_MERGE_THRESHOLD)
    review_threshold = float(settings.DUPLICATE_REVIEW_THRESHOLD)
    compatible_exact_rule = exact_rule and not conflicts and (attributes is None or attributes >= 60)
    if conflicts:
        decision = CandidateDecision.REJECTED
        final = 0.0
    elif compatible_exact_rule:
        decision = CandidateDecision.AUTO_MERGE
    elif final >= auto_threshold:
        decision = CandidateDecision.AUTO_MERGE
    elif final >= review_threshold:
        decision = CandidateDecision.NEEDS_REVIEW
    else:
        decision = CandidateDecision.REJECTED

    reasons = tuple(
        exact_reasons
        + location_reasons
        + attribute_reasons
        + text_reasons
        + image_reasons
        + price_reasons
    )
    return DuplicateEvaluation(
        exact_score=exact,
        address_score=address,
        geo_score=geo,
        attributes_score=attributes,
        text_score=text,
        image_score=image,
        price_score=price,
        final_score=final,
        decision=decision,
        reasons=reasons,
        hard_conflicts=tuple(conflicts),
        exact_rule=compatible_exact_rule,
    )
