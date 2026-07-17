from __future__ import annotations

import re
from decimal import Decimal
from typing import Iterable

from django.db.models import Q

from apps.analysis.contracts import RiskAssessmentResult, RiskSignal
from apps.analysis.models import (
    AnalysisStatus,
    ListingMarketAssessment,
    ListingPriceHistory,
    RiskLevel,
)
from apps.duplicates.models import DuplicateCandidate, ListingFingerprint
from apps.listings.models import Listing

PREPAYMENT_PHRASES = (
    "передоплат",
    "завдаток до перегляду",
    "бронювання до перегляду",
    "переказати кошти",
    "оплата наперед",
)
TEMPLATE_PHRASES = (
    "терміново",
    "без зайвих питань",
    "пишіть тільки в месенджер",
)
KNOWN_CITIES = ("львів", "рівне", "київ", "одеса", "дніпро", "харків")
URL_PATTERN = re.compile(r"https?://|(?:www\.)|(?:t\.me/)", re.IGNORECASE)


def _signal(
    code: str,
    weight: int,
    severity: str,
    label: str,
    recommendation: str,
    **evidence: object,
) -> RiskSignal:
    return RiskSignal(
        code=code,
        weight=weight,
        severity=severity,
        evidence=evidence,
        label=label,
        recommendation=recommendation,
    )


def _market_signal(
    market: ListingMarketAssessment | None,
) -> RiskSignal | None:
    if (
        market is None
        or market.status != AnalysisStatus.READY
        or market.deviation_percent is None
        or market.confidence_label not in {"medium", "high"}
    ):
        return None
    deviation = Decimal(market.deviation_percent)
    if deviation <= Decimal("-35"):
        return _signal(
            "price_far_below_market",
            30,
            "high",
            "Ціна значно нижча за ринковий орієнтир",
            "Перевірте право власності, документи та умови оплати до будь-якого переказу.",
            deviation_percent=str(deviation),
            confidence=market.confidence_label,
            comparable_count=market.comparable_count,
        )
    if deviation <= Decimal("-20"):
        return _signal(
            "price_below_market",
            18,
            "medium",
            "Ціна помітно нижча за схожі оголошення",
            "З'ясуйте причину нижчої ціни та перевірте документи під час особистого перегляду.",
            deviation_percent=str(deviation),
            confidence=market.confidence_label,
            comparable_count=market.comparable_count,
        )
    return None


def _price_history_signals(listing: Listing) -> list[RiskSignal]:
    events = list(ListingPriceHistory.objects.filter(listing=listing)[:10])
    if not events:
        return []
    largest = max(abs(Decimal(event.change_percent)) for event in events)
    signals: list[RiskSignal] = []
    if largest >= Decimal("30"):
        signals.append(
            _signal(
                "sharp_price_change",
                14,
                "medium",
                "Зафіксовано різку зміну ціни",
                "Уточніть актуальну ціну та повний перелік платежів у власника.",
                largest_change_percent=str(largest),
            )
        )
    if len(events) >= 3:
        signals.append(
            _signal(
                "frequent_price_changes",
                8,
                "low",
                "Ціна змінювалася декілька разів",
                "Попросіть письмово підтвердити остаточну ціну та умови договору.",
                event_count=len(events),
            )
        )
    return signals


def _duplicate_conflict_signal(listing: Listing) -> RiskSignal | None:
    candidate = (
        DuplicateCandidate.objects.filter(
            Q(left_listing=listing) | Q(right_listing=listing),
        )
        .exclude(hard_conflicts=[])
        .order_by("-final_score")
        .first()
    )
    if candidate is None:
        return None
    return _signal(
        "duplicate_hard_conflict",
        14,
        "medium",
        "У схожих публікаціях є суперечливі характеристики",
        "Порівняйте всі джерела та уточніть розбіжності перед домовленістю.",
        conflicts=list(candidate.hard_conflicts)[:8],
        candidate_id=str(candidate.id),
    )


def _cross_city_image_signal(listing: Listing) -> RiskSignal | None:
    try:
        fingerprint = listing.duplicate_fingerprint
    except Listing.duplicate_fingerprint.RelatedObjectDoesNotExist:
        return None
    current_hashes = {str(value) for value in fingerprint.image_hashes if value}
    attributes = listing.attributes if isinstance(listing.attributes, dict) else {}
    current_hashes.update(str(value) for value in attributes.get("demo_image_hashes", []) if value)
    if not current_hashes:
        return None
    others = (
        ListingFingerprint.objects.select_related("listing")
        .filter(listing__is_active=True)
        .exclude(listing=listing)
        .exclude(normalized_city=fingerprint.normalized_city)[:250]
    )
    matches: list[str] = []
    cities: set[str] = set()
    for other in others:
        other_hashes = {str(value) for value in other.image_hashes if value}
        other_attributes = (
            other.listing.attributes if isinstance(other.listing.attributes, dict) else {}
        )
        other_hashes.update(
            str(value) for value in other_attributes.get("demo_image_hashes", []) if value
        )
        if current_hashes.intersection(other_hashes):
            matches.append(str(other.listing_id))
            cities.add(other.listing.city)
    if not matches:
        return None
    return _signal(
        "images_reused_across_cities",
        24,
        "high",
        "Однакові перевірені image hashes знайдені в різних містах",
        "Попросіть актуальні фото або відеодзвінок із квартири та перевірте адресу.",
        matching_listing_ids=matches[:10],
        other_cities=sorted(cities),
    )


def _cluster_conflict_signal(listing: Listing) -> RiskSignal | None:
    try:
        membership = listing.cluster_membership
    except Listing.cluster_membership.RelatedObjectDoesNotExist:
        return None
    members = list(membership.cluster.members.select_related("listing"))
    if len(members) < 2:
        return None
    cities = {member.listing.city.casefold() for member in members}
    rooms = {member.listing.rooms for member in members}
    prices = [member.listing.price_uah for member in members if member.listing.price_uah > 0]
    price_spread = (
        (max(prices) - min(prices)) / min(prices) * 100 if len(prices) >= 2 and min(prices) else 0
    )
    conflicts: list[str] = []
    if len(cities) > 1:
        conflicts.append("city")
    if len(rooms) > 1:
        conflicts.append("rooms")
    if price_spread >= 25:
        conflicts.append("price")
    if not conflicts:
        return None
    return _signal(
        "cluster_source_conflicts",
        16,
        "medium",
        "Джерела однієї квартири містять суттєві розбіжності",
        "Відкрийте всі джерела кластера та уточніть актуальні характеристики.",
        conflicts=conflicts,
        price_spread_percent=round(price_spread, 2),
        member_count=len(members),
    )


def _content_signals(listing: Listing) -> list[RiskSignal]:
    text = f"{listing.title} {listing.description}".strip()
    normalized = text.casefold()
    signals: list[RiskSignal] = []
    if len(listing.description.strip()) < 80:
        signals.append(
            _signal(
                "short_description",
                8,
                "low",
                "Опис містить мало перевірюваних деталей",
                "Уточніть адресу, стан, платежі, договір і доступність квартири.",
                description_length=len(listing.description.strip()),
            )
        )
    matched_prepayment = [phrase for phrase in PREPAYMENT_PHRASES if phrase in normalized]
    if matched_prepayment:
        signals.append(
            _signal(
                "prepayment_language",
                30,
                "high",
                "В описі є вимога або натяк на оплату до перегляду",
                "Не переказуйте кошти до особистого перегляду, перевірки документів і договору.",
                matched_phrases=matched_prepayment,
            )
        )
    matched_templates = [phrase for phrase in TEMPLATE_PHRASES if phrase in normalized]
    if len(matched_templates) >= 2:
        signals.append(
            _signal(
                "template_pressure_language",
                7,
                "low",
                "Текст містить декілька фраз із тиском або шаблонністю",
                "Не поспішайте з рішенням і перевірте ключові факти незалежно.",
                matched_phrases=matched_templates,
            )
        )
    if URL_PATTERN.search(text):
        signals.append(
            _signal(
                "external_links_in_description",
                7,
                "low",
                "В описі є зовнішнє посилання",
                "Не вводьте платіжні або облікові дані на невідомих сторінках.",
                link_detected=True,
            )
        )
    other_cities = [city for city in KNOWN_CITIES if city != listing.city.casefold() and city in normalized]
    if other_cities:
        signals.append(
            _signal(
                "city_description_mismatch",
                12,
                "medium",
                "У тексті згадується інше місто",
                "Перевірте фактичне розташування квартири та адресу під час перегляду.",
                listing_city=listing.city,
                mentioned_cities=other_cities,
            )
        )
    return signals


def _missing_data_signal(listing: Listing) -> RiskSignal | None:
    missing: list[str] = []
    for field, value in (
        ("district", listing.district),
        ("street", listing.street),
        ("total_area", listing.total_area),
        ("floor", listing.floor),
        ("commission", listing.commission_percent),
        ("owner_status", listing.is_owner),
    ):
        if value in (None, ""):
            missing.append(field)
    if len(missing) < 3:
        return None
    return _signal(
        "missing_basic_fields",
        min(4 + len(missing), 12),
        "low",
        "В оголошенні бракує кількох базових параметрів",
        "Уточніть відсутні параметри та зафіксуйте їх у договорі.",
        missing_fields=missing,
    )


def _commission_signal(listing: Listing) -> RiskSignal | None:
    attributes = listing.attributes if isinstance(listing.attributes, dict) else {}
    if attributes.get("hidden_commission") is True:
        return _signal(
            "hidden_commission_hint",
            12,
            "medium",
            "Є ознака додаткової невказаної комісії",
            "Запитайте повну суму першого платежу та всі додаткові платежі письмово.",
            hidden_commission=True,
        )
    return None


def _protective_signals(listing: Listing) -> tuple[RiskSignal, ...]:
    protective: list[RiskSignal] = []
    if listing.is_owner is True:
        protective.append(
            _signal(
                "owner_declared",
                -5,
                "protective",
                "Автор указує, що є власником",
                "Усе одно перевірте документи, що підтверджують право власності.",
                is_owner=True,
            )
        )
    if len(listing.description.strip()) >= 300:
        protective.append(
            _signal(
                "detailed_description",
                -4,
                "protective",
                "Опис містить багато деталей",
                "Зіставте деталі з фактичним станом під час перегляду.",
                description_length=len(listing.description.strip()),
            )
        )
    return tuple(protective)


def _non_null(signals: Iterable[RiskSignal | None]) -> list[RiskSignal]:
    return [signal for signal in signals if signal is not None]


def calculate_risk_assessment(
    listing: Listing,
    market: ListingMarketAssessment | None,
) -> RiskAssessmentResult:
    signals = _non_null(
        (
            _market_signal(market),
            _duplicate_conflict_signal(listing),
            _cross_city_image_signal(listing),
            _cluster_conflict_signal(listing),
            _missing_data_signal(listing),
            _commission_signal(listing),
        )
    )
    signals.extend(_price_history_signals(listing))
    signals.extend(_content_signals(listing))
    protective = _protective_signals(listing)
    raw_score = sum(signal.weight for signal in signals) + sum(
        signal.weight for signal in protective
    )
    score = max(0, min(raw_score, 100))
    has_context = bool(
        listing.description.strip()
        or listing.total_area
        or market is not None
        or signals
        or protective
    )
    if not has_context:
        status = AnalysisStatus.INSUFFICIENT_DATA
        level = RiskLevel.INSUFFICIENT_DATA
        summary = "Недостатньо даних для допоміжної оцінки ризику."
    elif score >= 50:
        status = AnalysisStatus.READY
        level = RiskLevel.ELEVATED
        summary = "Підвищений потенційний ризик: перевірте наведені сигнали."
    elif score >= 25:
        status = AnalysisStatus.READY
        level = RiskLevel.REVIEW
        summary = "Є моменти, які варто додатково перевірити."
    else:
        status = AnalysisStatus.READY
        level = RiskLevel.LOW
        summary = "Низький потенційний ризик за доступними даними."
    return RiskAssessmentResult(
        status=status,
        score=score,
        level=level,
        signals=tuple(signals),
        protective_signals=protective,
        summary=summary,
        safety_advice=(
            "Допоміжна оцінка не є юридичним висновком. Перевірте особу, документи, "
            "право власності й договір та не переказуйте кошти до перегляду квартири."
        ),
    )
