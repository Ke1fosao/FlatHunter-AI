from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from asgiref.sync import sync_to_async
from django.db import transaction
from django.utils import timezone

from apps.listings.contracts import ListingSourceAdapter, SourceSearchRequest
from apps.listings.models import Listing, ListingSource, RawListing


class SourceUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class IngestionResult:
    received: int
    created: int
    updated: int
    unchanged: int
    failed: int


@dataclass(frozen=True)
class PreparedRawListing:
    raw: RawListing
    payload_hash: str
    external_id: str


def _payload_hash(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()
    return hashlib.sha256(encoded).hexdigest()


@sync_to_async
@transaction.atomic
def _prepare_raw_listing(
    source: ListingSource,
    payload: dict[str, Any],
    external_id: str,
) -> PreparedRawListing:
    payload_hash = _payload_hash(payload)
    raw, _ = RawListing.objects.get_or_create(
        source=source,
        external_id=external_id,
        payload_hash=payload_hash,
        defaults={"payload": payload, "expires_at": timezone.now() + timedelta(days=30)},
    )
    return PreparedRawListing(raw=raw, payload_hash=payload_hash, external_id=external_id)


@sync_to_async
@transaction.atomic
def _persist_normalized_listing(
    source: ListingSource,
    prepared: PreparedRawListing,
    values: dict[str, Any],
) -> str:
    listing, created = Listing.objects.update_or_create(
        source=source,
        external_id=prepared.external_id,
        defaults={**values, "raw_listing": prepared.raw},
    )
    if prepared.raw.normalized_at is None or prepared.raw.normalization_error:
        prepared.raw.normalized_at = timezone.now()
        prepared.raw.normalization_error = ""
        prepared.raw.save(update_fields=("normalized_at", "normalization_error"))
    from apps.analysis.services import capture_and_optionally_refresh
    from apps.duplicates.services import schedule_listing_duplicate_refresh

    transaction.on_commit(lambda: capture_and_optionally_refresh(listing.id))
    transaction.on_commit(lambda: schedule_listing_duplicate_refresh(listing.id))
    return "created" if created else "updated"


@sync_to_async
def _mark_raw_failure(raw: RawListing, error: Exception) -> None:
    raw.normalization_error = f"{type(error).__name__}: {error}"[:2000]
    raw.normalized_at = None
    raw.save(update_fields=("normalization_error", "normalized_at"))


@sync_to_async
def _touch_unchanged_listing(source: ListingSource, external_id: str) -> None:
    Listing.objects.filter(source=source, external_id=external_id).update(
        last_seen_at=timezone.now(),
        is_active=True,
    )


@sync_to_async
def _mark_source_error(source: ListingSource) -> None:
    source.last_error_at = timezone.now()
    source.health_status = "degraded"
    source.save(update_fields=("last_error_at", "health_status"))


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
            "access_mode": adapter.access_mode,
            "legal_status": adapter.legal_status,
            "health_status": "healthy",
        },
    )
    if not created_source and (
        not source.enabled or source.legal_status not in {"approved_demo", "approved"}
    ):
        raise SourceUnavailableError("Source is disabled or has no approved legal status")

    if not created_source:
        changed_fields: list[str] = []
        if source.display_name != adapter.display_name:
            source.display_name = adapter.display_name
            changed_fields.append("display_name")
        if source.access_mode != adapter.access_mode:
            source.access_mode = adapter.access_mode
            changed_fields.append("access_mode")
        if changed_fields:
            await source.asave(update_fields=changed_fields)

    try:
        raw_items = await adapter.search(request)
    except Exception:
        await _mark_source_error(source)
        raise

    created = 0
    updated = 0
    unchanged = 0
    failed = 0

    for raw_item in raw_items:
        prepared: PreparedRawListing | None = None
        try:
            external_id = adapter.external_id_from_raw(raw_item)
            prepared = await _prepare_raw_listing(source, raw_item, external_id)
            normalized = await adapter.normalize(raw_item)
            if normalized.external_id != external_id:
                raise ValueError("normalized external_id differs from raw external_id")

            current_hash = await (
                Listing.objects.filter(source=source, external_id=external_id)
                .values_list("raw_listing__payload_hash", flat=True)
                .afirst()
            )
            if current_hash == prepared.payload_hash:
                await _touch_unchanged_listing(source, external_id)
                unchanged += 1
                continue

            result_status = await _persist_normalized_listing(source, prepared, normalized.values)
            created += int(result_status == "created")
            updated += int(result_status == "updated")
        except Exception as error:
            failed += 1
            if prepared is not None:
                await _mark_raw_failure(prepared.raw, error)

    source.last_success_at = timezone.now()
    source.health_status = "healthy" if failed == 0 else "degraded"
    update_fields = ["last_success_at", "health_status"]
    if failed:
        source.last_error_at = timezone.now()
        update_fields.append("last_error_at")
    await source.asave(update_fields=update_fields)

    return IngestionResult(
        received=len(raw_items),
        created=created,
        updated=updated,
        unchanged=unchanged,
        failed=failed,
    )
