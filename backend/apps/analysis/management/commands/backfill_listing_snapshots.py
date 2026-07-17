from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.snapshots import capture_listing_snapshot


class Command(BaseCommand):
    help = "Create idempotent baseline snapshots for approved active listings."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        configured_batch = int(getattr(settings, "ANALYSIS_BATCH_SIZE", 100))
        batch_size = min(max(int(options["batch_size"] or configured_batch), 1), 500)
        limit = max(int(options["limit"]), 0)
        queryset = approved_listing_queryset().order_by("id")
        if limit:
            queryset = queryset[:limit]
        total = queryset.count() if not limit else min(queryset.count(), limit)
        if options["dry_run"]:
            self.stdout.write(
                f"Snapshot backfill dry-run: eligible={total}, batch_size={batch_size}"
            )
            return

        created = 0
        unchanged = 0
        for listing in queryset.iterator(chunk_size=batch_size):
            result = capture_listing_snapshot(listing)
            created += int(result.created)
            unchanged += int(not result.created)
        self.stdout.write(
            self.style.SUCCESS(
                f"Snapshot backfill: eligible={total}, created={created}, unchanged={unchanged}"
            )
        )
