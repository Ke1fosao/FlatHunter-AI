from __future__ import annotations

from decimal import Decimal
from typing import Any

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand

from apps.geodata.contracts import GeocodingError, GeocodingRequest
from apps.geodata.service import geocode_address
from apps.listings.models import Listing
from apps.searches.models import ImportantPlace


class Command(BaseCommand):
    help = "Backfill PostGIS points for demo listings and important places."

    def handle(self, *args: Any, **options: Any) -> None:
        processed = 0
        updated = 0
        unchanged = 0
        failed = 0

        for listing in Listing.objects.filter(is_active=True).iterator(chunk_size=500):
            processed += 1
            if listing.location is not None:
                unchanged += 1
                continue
            if listing.latitude is None or listing.longitude is None:
                failed += 1
                continue
            listing.save(update_fields=("latitude", "longitude", "location"))
            updated += 1

        for place in ImportantPlace.objects.select_related("search_profile").iterator(
            chunk_size=200
        ):
            processed += 1
            if place.location is not None:
                unchanged += 1
                continue
            if place.latitude is not None and place.longitude is not None:
                place.save(update_fields=("latitude", "longitude", "location"))
                updated += 1
                continue
            if not place.address:
                failed += 1
                continue
            try:
                result = async_to_sync(geocode_address)(
                    GeocodingRequest(query=place.address, city=place.search_profile.city)
                )
            except GeocodingError:
                failed += 1
                continue
            place.latitude = Decimal(str(result.latitude))
            place.longitude = Decimal(str(result.longitude))
            place.geocoding_provider = result.provider
            place.geocoding_confidence = Decimal(str(result.confidence))
            place.save()
            updated += 1

        summary = (
            f"Geodata backfill: processed={processed}, updated={updated}, "
            f"unchanged={unchanged}, failed={failed}"
        )
        if failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
