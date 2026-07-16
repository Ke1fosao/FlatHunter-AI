from __future__ import annotations

from dataclasses import asdict
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.duplicates.candidates import detect_listing_duplicates


class Command(BaseCommand):
    help = "Evaluate bounded duplicate candidates and persist explainable scores."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--listing-id")
        parser.add_argument("--city")
        parser.add_argument("--limit", type=int)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        result = detect_listing_duplicates(
            listing_id=options["listing_id"] or None,
            city=options["city"] or None,
            limit=options["limit"],
            dry_run=bool(options["dry_run"]),
        )
        summary = ", ".join(f"{field}={value}" for field, value in asdict(result).items())
        self.stdout.write(
            self.style.WARNING(summary) if result.failed else self.style.SUCCESS(summary)
        )
