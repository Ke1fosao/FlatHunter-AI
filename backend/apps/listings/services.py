from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.listings.contracts import ListingSourceAdapter, SourceSearchRequest
from apps.listings.models import Listing, ListingSource, RawListing, SourceAccessMode


class SourceUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestionResult:
    received: int
    created: int
    updated: int
    unchanged: int


def _payload_hash(payload: dict[str, object]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@sync_to_async
@transaction.atomic
def _persist_listing(
    source: ListingSource,
    payload: dict[str, object],
    external_id: str,
    values: dict[str, object],
) -> str:
    payload_hash = _payload_hash(payload)
    raw, _ = RawListing.objects.get_or_create(
        source=source,
        external_id=external_id,
        payload_hash=payload_hash,
        defaults={"payload": payload, "expires_at": timezone.now() + timedelta(days=30)},
    )
    _listing, created = Listing.objects.update_or_create(
        source=source,
        external_id=external_id,
        defaults={**values, "raw_listing": raw},
    )
    if raw.normalized_at is None:
        raw.normalized_at = timezone.now()
        raw.normalization_error = ""
        raw.save(update_fields=("normalized_at", "normalization_error"))
    return "created" if created else "updated"


async def ingest_source(
    adapter: ListingSourceAdapter,
    request: SourceSearchRequest,
) -> IngestionResult:
    health = await adapter.health_check()
    if not health.healthy:
        raise SourceUnavailableError(health.message)

    source, created_source = await ListingSource.objects.aget_or_create(
        code=adapter.source_code,
        defaults={
            "display_name": adapter.display_name,
            "enabled": True,
            "access_mode": SourceAccessMode.DEMO,
            "legal_status": "approved_demo",
            "health_status": "healthy",
        },
    )
    if not created_source and (
        not source.enabled or source.legal_status not in {"approved_demo", "approved"}
    ):
        raise SourceUnavailableError("Source is disabled or has no approved legal status")

    raw_items = await adapter.search(request)
    created = 0
    updated = 0
    unchanged = 0
    for raw_item in raw_items:
        normalized = await adapter.normalize(raw_item)
        current_hash = await Listing.objects.filter(
            source=source,
            external_id=normalized.external_id,
        ).values_list("raw_listing__payload_hash", flat=True).afirst()
        if current_hash == _payload_hash(raw_item):
            unchanged += 1
            continue
        status = await _persist_listing(source, raw_item, normalized.external_id, normalized.values)
        created += int(status == "created")
        updated += int(status == "updated")

    source.last_success_at = timezone.now()
    source.health_status = "healthy"
    await source.asave(update_fields=("last_success_at", "health_status"))
    return IngestionResult(len(raw_items), created, updated, unchanged)
