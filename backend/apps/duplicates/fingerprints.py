from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.db import transaction

from apps.duplicates.models import ListingFingerprint
from apps.duplicates.normalization import (
    FINGERPRINT_VERSION,
    IMAGE_HASH_VERSION,
    address_key,
    attribute_key,
    canonicalize_url,
    contact_hashes,
    geo_block_key,
    normalize_text,
    price_bucket,
    simhash64,
    trusted_image_hashes,
)
from apps.listings.models import Listing


@dataclass(frozen=True)
class FingerprintBuildResult:
    fingerprint: ListingFingerprint | None
    created: bool
    changed: bool
    error: str = ""


def fingerprint_defaults(listing: Listing) -> dict[str, Any]:
    normalized_title = normalize_text(listing.title)
    normalized_description = normalize_text(listing.description)
    combined_text = f"{normalized_title} {normalized_description}".strip()
    text_hash = simhash64(combined_text)
    return {
        "version": FINGERPRINT_VERSION,
        "normalized_city": normalize_text(listing.city),
        "normalized_district": normalize_text(listing.district),
        "normalized_street": normalize_text(listing.street),
        "normalized_title": normalized_title[:500],
        "normalized_description": normalized_description,
        "normalized_url": canonicalize_url(listing.canonical_url or listing.source_url),
        "address_key": address_key(listing),
        "geo_block_key": geo_block_key(listing),
        "attribute_key": attribute_key(listing),
        "price_bucket": price_bucket(listing.price_uah),
        "text_simhash": text_hash,
        "text_block_key": text_hash[:4] if text_hash else "",
        "contact_hashes": contact_hashes(listing),
        "image_hashes": trusted_image_hashes(listing),
        "image_hash_version": IMAGE_HASH_VERSION,
        "source_updated_at": listing.last_seen_at,
        "last_error": "",
    }


def fingerprint_is_stale(listing: Listing, fingerprint: ListingFingerprint | None) -> bool:
    if fingerprint is None:
        return True
    return (
        fingerprint.version != FINGERPRINT_VERSION
        or fingerprint.image_hash_version != IMAGE_HASH_VERSION
        or fingerprint.source_updated_at < listing.last_seen_at
    )


@transaction.atomic
def build_listing_fingerprint(listing: Listing, *, force: bool = False) -> FingerprintBuildResult:
    existing = ListingFingerprint.objects.select_for_update().filter(listing=listing).first()
    if not force and not fingerprint_is_stale(listing, existing):
        return FingerprintBuildResult(existing, created=False, changed=False)
    try:
        defaults = fingerprint_defaults(listing)
        fingerprint, created = ListingFingerprint.objects.update_or_create(
            listing=listing,
            defaults=defaults,
        )
        return FingerprintBuildResult(fingerprint, created=created, changed=True)
    except Exception as error:
        message = f"{type(error).__name__}: {error}"[:500]
        if existing is not None:
            existing.last_error = message
            existing.save(update_fields=("last_error", "generated_at"))
        return FingerprintBuildResult(existing, created=False, changed=False, error=message)


def get_fresh_fingerprint(listing: Listing) -> ListingFingerprint:
    result = build_listing_fingerprint(listing)
    if result.fingerprint is None:
        raise RuntimeError(result.error or "Unable to build listing fingerprint")
    return result.fingerprint
