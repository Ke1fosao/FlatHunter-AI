from __future__ import annotations

from dataclasses import asdict

from celery import shared_task

from apps.duplicates.candidates import detect_listing_duplicates
from apps.duplicates.clustering import rebuild_clusters
from apps.duplicates.fingerprints import build_listing_fingerprint
from apps.duplicates.services import refresh_listing_duplicates
from apps.listings.models import Listing


@shared_task(name="apps.duplicates.tasks.refresh_listing_duplicates_task")
def refresh_listing_duplicates_task(listing_id: str) -> dict[str, int | bool]:
    result = refresh_listing_duplicates(listing_id)
    return {
        "fingerprint_changed": result.fingerprint.changed,
        "candidate_pairs": result.candidates.inspected,
        "clusters": result.clusters.components,
    }


@shared_task(name="apps.duplicates.tasks.build_listing_fingerprint_task")
def build_listing_fingerprint_task(listing_id: str) -> dict[str, bool | str]:
    result = build_listing_fingerprint(Listing.objects.get(pk=listing_id), force=True)
    return {"changed": result.changed, "error": result.error}


@shared_task(name="apps.duplicates.tasks.detect_listing_duplicates_task")
def detect_listing_duplicates_task(city: str = "") -> dict[str, int]:
    result = detect_listing_duplicates(city=city or None)
    return {key: int(value) for key, value in asdict(result).items()}


@shared_task(name="apps.duplicates.tasks.rebuild_listing_clusters_task")
def rebuild_listing_clusters_task(city: str = "") -> dict[str, int]:
    result = rebuild_clusters(city=city or None)
    return {key: int(value) for key, value in asdict(result).items()}
