from __future__ import annotations

from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.contrib.gis.measure import D
from django.core.exceptions import ObjectDoesNotExist
from django.db.models import Q, QuerySet
from django.utils import timezone

from apps.analysis.contracts import ComparableListing, ComparableSet
from apps.listings.models import Listing


def _approved_candidates(listing: Listing) -> QuerySet[Listing]:
    freshness_days = max(int(getattr(settings, "MARKET_FRESHNESS_DAYS", 90)), 1)
    queryset = Listing.objects.filter(
        is_active=True,
        source__enabled=True,
        source__legal_status__in=("approved_demo", "approved"),
        city__iexact=listing.city,
        price_uah__gt=0,
        published_at__gte=timezone.now() - timedelta(days=freshness_days),
    ).exclude(pk=listing.pk)
    queryset = queryset.filter(
        Q(cluster_membership__isnull=True) | Q(cluster_membership__role="primary")
    )
    try:
        membership = listing.cluster_membership
    except ObjectDoesNotExist:
        membership = None
    if membership is not None:
        queryset = queryset.exclude(cluster_membership__cluster=membership.cluster)
    return queryset


def _area_bounds(listing: Listing, percent: float) -> tuple[Decimal, Decimal] | None:
    if listing.total_area is None or listing.total_area <= 0:
        return None
    tolerance = Decimal(str(max(percent, 0))) / Decimal("100")
    return (
        listing.total_area * (Decimal("1") - tolerance),
        listing.total_area * (Decimal("1") + tolerance),
    )


def _apply_area(queryset: QuerySet[Listing], listing: Listing, percent: float) -> QuerySet[Listing]:
    bounds = _area_bounds(listing, percent)
    if bounds is None:
        return queryset
    return queryset.filter(total_area__gte=bounds[0], total_area__lte=bounds[1])


def _choose_stage(listing: Listing) -> tuple[QuerySet[Listing], str, int]:
    minimum = max(int(getattr(settings, "MARKET_MIN_COMPARABLES", 8)), 2)
    base = _approved_candidates(listing).filter(rooms=listing.rooms)
    tolerance = float(getattr(settings, "MARKET_AREA_TOLERANCE_PERCENT", 25.0))

    stages: list[tuple[str, QuerySet[Listing]]] = []
    if listing.district:
        district = _apply_area(
            base.filter(district__iexact=listing.district),
            listing,
            min(tolerance, 20.0),
        )
        stages.append(("district_rooms_area", district))
    if listing.location is not None:
        radius = max(float(getattr(settings, "MARKET_RADIUS_KM", 5.0)), 0.1)
        nearby = _apply_area(
            base.filter(location__distance_lte=(listing.location, D(km=radius))),
            listing,
            tolerance,
        )
        stages.append(("radius_rooms_area", nearby))
    attribute_filter = Q()
    if listing.building_type:
        attribute_filter |= Q(building_type=listing.building_type)
    if listing.renovation_level:
        attribute_filter |= Q(renovation_level=listing.renovation_level)
    if attribute_filter:
        stages.append(("city_rooms_attributes", base.filter(attribute_filter)))
    stages.append(("city_rooms", base))

    selected_name = stages[-1][0]
    selected = stages[-1][1]
    count = selected.count()
    for stage_name, stage_queryset in stages:
        stage_count = stage_queryset.count()
        selected_name, selected, count = stage_name, stage_queryset, stage_count
        if stage_count >= minimum:
            break
    return selected, selected_name, count


def select_local_comparables(listing: Listing) -> ComparableSet:
    queryset, stage, candidate_count = _choose_stage(listing)
    maximum = max(int(getattr(settings, "MARKET_MAX_COMPARABLES", 120)), 2)
    rows = list(queryset.order_by("-published_at", "price_uah", "id")[:maximum])
    items = tuple(
        ComparableListing(
            id=row.id,
            price_uah=int(row.price_uah),
            total_area=row.total_area,
            city=row.city,
            district=row.district,
            building_type=row.building_type,
            renovation_level=row.renovation_level,
            location_accuracy=row.location_accuracy,
            published_at=row.published_at,
            selection_stage=stage,
        )
        for row in rows
    )
    return ComparableSet(
        items=items,
        selection_stage=stage,
        candidate_count=candidate_count,
        limit_applied=candidate_count > maximum,
    )
