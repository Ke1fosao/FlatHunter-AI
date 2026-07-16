from __future__ import annotations

from dataclasses import asdict
from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from apps.duplicates.clustering import rebuild_clusters


class Command(BaseCommand):
    help = "Rebuild active listing clusters from accepted duplicate edges."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--city")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args: Any, **options: Any) -> None:
        result = rebuild_clusters(
            city=options["city"] or None,
            dry_run=bool(options["dry_run"]),
        )
        summary = ", ".join(f"{field}={value}" for field, value in asdict(result).items())
        self.stdout.write(self.style.SUCCESS(summary))
