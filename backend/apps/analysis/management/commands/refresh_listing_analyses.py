from __future__ import annotations

from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandParser

from apps.analysis.querysets import approved_listing_queryset
from apps.analysis.services import refresh_listing_analysis


class Command(BaseCommand):
    help = "Build or refresh deterministic market and risk assessments in bounded batches."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument("--batch-size", type=int, default=0)
        parser.add_argument("--force", action="store_true")
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
                f"Analysis refresh dry-run: eligible={total}, batch_size={batch_size}"
            )
            return

        ready = 0
        insufficient = 0
        failed = 0
        for listing in queryset.iterator(chunk_size=batch_size):
            result = refresh_listing_analysis(listing.id, force=bool(options["force"]))
            statuses = {result.market.status, result.risk.status}
            ready += int("ready" in statuses)
            insufficient += int("insufficient_data" in statuses)
            failed += int("failed" in statuses)
        self.stdout.write(
            self.style.SUCCESS(
                "Analysis refresh: "
                f"eligible={total}, ready={ready}, insufficient={insufficient}, failed={failed}"
            )
        )
