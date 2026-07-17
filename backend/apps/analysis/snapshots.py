from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from typing import Any

from django.db import transaction

from apps.analysis.models import ListingPriceHistory, ListingSnapshot, PriceDirection
from apps.listings.models import Listing

ALLOWED_ATTRIBUTE_KEYS = (
    "backup_power",
    "balcony",
    "building_number",
    "demo",
    "demo_duplicate_group",
    "demo_image_hashes",
    "demo_revision",
    "elevator",
    "furniture",
    "parking",
    "relisted_count",
)


@dataclass(frozen=True)
class SnapshotCaptureResult:
    snapshot: ListingSnapshot
    created: bool
    price_event: ListingPriceHistory | None


def _decimal_value(value: Decimal | None) -> str | None:
    return str(value) if value is not None else None


def _text_hash(value: str) -> str:
    return hashlib.sha256(value.strip().encode("utf-8")).hexdigest()


def canonical_snapshot_payload(listing: Listing) -> dict[str, Any]:
    attributes = listing.attributes if isinstance(listing.attributes, dict) else {}
    attributes_summary = {
        key: attributes[key]
        for key in ALLOWED_ATTRIBUTE_KEYS
        if key in attributes
    }
    return {
        "price_uah": int(listing.price_uah),
        "currency": listing.currency,
        "title_hash": _text_hash(listing.title),
        "description_hash": _text_hash(listing.description),
        "city": listing.city.strip(),
        "district": listing.district.strip(),
        "street": listing.street.strip(),
        "rooms": int(listing.rooms),
        "total_area": _decimal_value(listing.total_area),
        "floor": listing.floor,
        "floors_total": listing.floors_total,
        "building_type": listing.building_type,
        "renovation_level": listing.renovation_level,
        "heating_type": listing.heating_type,
        "pets_allowed": listing.pets_allowed,
        "children_allowed": listing.children_allowed,
        "commission_percent": _decimal_value(listing.commission_percent),
        "is_owner": listing.is_owner,
        "attributes_summary": attributes_summary,
        "is_active": bool(listing.is_active),
        "source_last_seen_at": listing.last_seen_at.isoformat() if listing.last_seen_at else None,
    }


def snapshot_content_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _snapshot_defaults(payload: dict[str, Any]) -> dict[str, Any]:
    return {
        "price_uah": payload["price_uah"],
        "currency": payload["currency"],
        "title_hash": payload["title_hash"],
        "description_hash": payload["description_hash"],
        "city": payload["city"],
        "district": payload["district"],
        "street": payload["street"],
        "rooms": payload["rooms"],
        "total_area": payload["total_area"],
        "floor": payload["floor"],
        "floors_total": payload["floors_total"],
        "building_type": payload["building_type"],
        "renovation_level": payload["renovation_level"],
        "heating_type": payload["heating_type"],
        "pets_allowed": payload["pets_allowed"],
        "children_allowed": payload["children_allowed"],
        "commission_percent": payload["commission_percent"],
        "is_owner": payload["is_owner"],
        "attributes_summary": payload["attributes_summary"],
        "is_active": payload["is_active"],
        "source_last_seen_at": payload["source_last_seen_at"],
    }


@transaction.atomic
def capture_listing_snapshot(listing: Listing) -> SnapshotCaptureResult:
    locked_listing = Listing.objects.select_for_update().get(pk=listing.pk)
    payload = canonical_snapshot_payload(locked_listing)
    content_hash = snapshot_content_hash(payload)
    previous = (
        ListingSnapshot.objects.filter(listing=locked_listing)
        .order_by("-captured_at", "-id")
        .first()
    )
    snapshot, created = ListingSnapshot.objects.get_or_create(
        listing=locked_listing,
        content_hash=content_hash,
        defaults=_snapshot_defaults(payload),
    )
    if not created or previous is None or previous.price_uah == snapshot.price_uah:
        return SnapshotCaptureResult(snapshot=snapshot, created=created, price_event=None)

    change_amount = snapshot.price_uah - previous.price_uah
    change_percent = (
        Decimal(change_amount) / Decimal(previous.price_uah) * Decimal("100")
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    event, _ = ListingPriceHistory.objects.get_or_create(
        snapshot=snapshot,
        defaults={
            "listing": locked_listing,
            "previous_price_uah": previous.price_uah,
            "new_price_uah": snapshot.price_uah,
            "change_amount_uah": change_amount,
            "change_percent": change_percent,
            "direction": (
                PriceDirection.INCREASE if change_amount > 0 else PriceDirection.DECREASE
            ),
            "changed_at": snapshot.captured_at,
        },
    )
    return SnapshotCaptureResult(snapshot=snapshot, created=True, price_event=event)
