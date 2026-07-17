from __future__ import annotations

import statistics
from decimal import Decimal, ROUND_HALF_UP

from django.conf import settings
from django.utils import timezone

from apps.analysis.contracts import ComparableSet, MarketAssessmentResult
from apps.analysis.models import AnalysisStatus, ConfidenceLabel
from apps.listings.models import Listing

TWOPLACES = Decimal("0.01")


def _money(value: int | float | Decimal) -> int:
    return int(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))


def _decimal(value: int | float | Decimal) -> Decimal:
    return Decimal(str(value)).quantize(TWOPLACES, rounding=ROUND_HALF_UP)


def _quartiles(prices: list[int]) -> tuple[int, int]:
    if len(prices) < 2:
        return prices[0], prices[0]
    q1, _, q3 = statistics.quantiles(prices, n=4, method="inclusive")
    return _money(q1), _money(q3)


def _confidence(
    listing: Listing,
    comparables: ComparableSet,
    median_price: int,
    q1_price: int,
    q3_price: int,
) -> tuple[Decimal, str, dict[str, object]]:
    count = len(comparables.items)
    minimum = max(int(getattr(settings, "MARKET_MIN_COMPARABLES", 8)), 2)
    maximum = max(int(getattr(settings, "MARKET_MAX_COMPARABLES", 120)), minimum)
    sample_component = min(count / max(minimum * 2, 1), 1.0) * 35
    district_matches = sum(
        1
        for item in comparables.items
        if listing.district and item.district.casefold() == listing.district.casefold()
    )
    geography_component = (district_matches / count if count else 0) * 20
    area_count = sum(1 for item in comparables.items if item.total_area and item.total_area > 0)
    area_component = (area_count / count if count else 0) * 15
    now = timezone.now()
    freshness_days = max(int(getattr(settings, "MARKET_FRESHNESS_DAYS", 90)), 1)
    average_age = (
        sum(max((now - item.published_at).total_seconds() / 86400, 0) for item in comparables.items)
        / count
        if count
        else freshness_days
    )
    freshness_component = max(0.0, 1 - average_age / freshness_days) * 15
    dispersion_ratio = (q3_price - q1_price) / median_price if median_price else 1
    dispersion_component = max(0.0, 1 - min(dispersion_ratio, 1.0)) * 15
    score = min(
        sample_component
        + geography_component
        + area_component
        + freshness_component
        + dispersion_component,
        100,
    )
    score_decimal = _decimal(score)
    if count < minimum:
        label = ConfidenceLabel.LOW
    elif score_decimal >= Decimal("75"):
        label = ConfidenceLabel.HIGH
    elif score_decimal >= Decimal("50"):
        label = ConfidenceLabel.MEDIUM
    else:
        label = ConfidenceLabel.LOW
    return score_decimal, label, {
        "sample_component": round(sample_component, 2),
        "geography_component": round(geography_component, 2),
        "area_component": round(area_component, 2),
        "freshness_component": round(freshness_component, 2),
        "dispersion_component": round(dispersion_component, 2),
        "configured_minimum": minimum,
        "configured_maximum": maximum,
    }


def calculate_market_assessment(
    listing: Listing,
    comparables: ComparableSet,
) -> MarketAssessmentResult:
    prices = sorted(item.price_uah for item in comparables.items if item.price_uah > 0)
    minimum = max(int(getattr(settings, "MARKET_MIN_COMPARABLES", 8)), 2)
    if not prices:
        return MarketAssessmentResult(
            status=AnalysisStatus.INSUFFICIENT_DATA,
            median_price_uah=None,
            q1_price_uah=None,
            q3_price_uah=None,
            median_price_per_sqm=None,
            target_price_per_sqm=None,
            deviation_percent=None,
            comparable_count=0,
            confidence_score=Decimal("0.00"),
            confidence_label=ConfidenceLabel.NONE,
            comparable_ids=(),
            selection_summary={
                "selection_stage": comparables.selection_stage,
                "candidate_count": comparables.candidate_count,
                "outlier_count": 0,
                "limit_applied": comparables.limit_applied,
            },
            explanation="Недостатньо схожих активних оголошень для ринкової оцінки.",
        )

    median_price = _money(statistics.median(prices))
    q1_price, q3_price = _quartiles(prices)
    iqr = q3_price - q1_price
    lower_fence = q1_price - Decimal("1.5") * Decimal(iqr)
    upper_fence = q3_price + Decimal("1.5") * Decimal(iqr)
    outlier_count = sum(
        1 for price in prices if Decimal(price) < lower_fence or Decimal(price) > upper_fence
    )
    per_square_meter = sorted(
        Decimal(item.price_uah) / item.total_area
        for item in comparables.items
        if item.total_area is not None and item.total_area > 0
    )
    median_per_sqm = (
        _decimal(statistics.median(per_square_meter)) if per_square_meter else None
    )
    target_per_sqm = (
        _decimal(Decimal(listing.price_uah) / listing.total_area)
        if listing.total_area is not None and listing.total_area > 0
        else None
    )
    deviation = (
        _decimal(
            (Decimal(listing.price_uah) - Decimal(median_price))
            / Decimal(median_price)
            * Decimal("100")
        )
        if median_price
        else None
    )
    confidence_score, confidence_label, confidence_components = _confidence(
        listing,
        comparables,
        median_price,
        q1_price,
        q3_price,
    )
    enough = len(prices) >= minimum
    explanation = (
        f"Використано {len(prices)} схожих оголошень; медіанний діапазон "
        f"{q1_price:,}–{q3_price:,} грн.".replace(",", " ")
        if enough
        else (
            f"Знайдено {len(prices)} схожих оголошень, але для надійної оцінки "
            f"потрібно щонайменше {minimum}."
        )
    )
    return MarketAssessmentResult(
        status=AnalysisStatus.READY if enough else AnalysisStatus.INSUFFICIENT_DATA,
        median_price_uah=median_price if enough else None,
        q1_price_uah=q1_price if enough else None,
        q3_price_uah=q3_price if enough else None,
        median_price_per_sqm=median_per_sqm if enough else None,
        target_price_per_sqm=target_per_sqm if enough else None,
        deviation_percent=deviation if enough else None,
        comparable_count=len(prices),
        confidence_score=confidence_score,
        confidence_label=confidence_label,
        comparable_ids=comparables.ids,
        selection_summary={
            "selection_stage": comparables.selection_stage,
            "candidate_count": comparables.candidate_count,
            "outlier_count": outlier_count,
            "limit_applied": comparables.limit_applied,
            "confidence_components": confidence_components,
        },
        explanation=explanation,
    )
