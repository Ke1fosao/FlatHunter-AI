from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.duplicates.fingerprints import build_listing_fingerprint
from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Refresh trusted/offline image fingerprint metadata without downloading remote images."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--listing-id")
        parser.add_argument("--city")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        queryset = Listing.objects.filter(is_active=True).select_related("source").order_by("id")
        if options["listing_id"]:
            queryset = queryset.filter(pk=options["listing_id"])
        if options["city"]:
            queryset = queryset.filter(city__iexact=options["city"])
        if options["limit"]:
            queryset = queryset[: max(1, min(int(options["limit"]), 5000))]
        inspected = changed = failed = 0
        for listing in queryset.iterator(chunk_size=200):
            inspected += 1
            if options["dry_run"]:
                continue
            result = build_listing_fingerprint(listing, force=True)
            changed += int(result.changed)
            failed += int(bool(result.error))
        summary = (
            f"Image fingerprints: inspected={inspected}, changed={changed}, failed={failed}, "
            f"remote_fetch=false, dry_run={bool(options['dry_run'])}"
        )
        self.stdout.write(self.style.WARNING(summary) if failed else self.style.SUCCESS(summary))
