from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.duplicates.fingerprints import build_listing_fingerprint, fingerprint_defaults
from apps.listings.models import Listing


class Command(BaseCommand):
    help = "Build or refresh deterministic listing fingerprints."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--listing-id")
        parser.add_argument("--city")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        queryset = Listing.objects.filter(is_active=True).select_related("source").order_by("id")
        if options["listing_id"]:
            queryset = queryset.filter(pk=options["listing_id"])
        if options["city"]:
            queryset = queryset.filter(city__iexact=options["city"])
        if options["limit"]:
            queryset = queryset[: max(1, min(int(options["limit"]), 5000))]
        inspected = created = changed = failed = 0
        for listing in queryset.iterator(chunk_size=200):
            inspected += 1
            if options["dry_run"]:
                fingerprint_defaults(listing)
                continue
            result = build_listing_fingerprint(listing, force=bool(options["force"]))
            created += int(result.created)
            changed += int(result.changed)
            failed += int(bool(result.error))
        message = (
            f"Fingerprints: inspected={inspected}, created={created}, changed={changed}, "
            f"failed={failed}, dry_run={bool(options['dry_run'])}"
        )
        self.stdout.write(self.style.WARNING(message) if failed else self.style.SUCCESS(message))
