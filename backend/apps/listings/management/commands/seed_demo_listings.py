from typing import Any

from asgiref.sync import async_to_sync
from django.core.management.base import BaseCommand, CommandParser

from apps.listings.contracts import SourceSearchRequest
from apps.listings.demo_source import DemoListingSourceAdapter
from apps.listings.services import ingest_source


class Command(BaseCommand):
    help = "Create or refresh deterministic synthetic demo listings."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("--count", type=int, default=150)
        parser.add_argument("--seed", type=int, default=20260716)
        parser.add_argument("--revision", type=int, default=1)

    def handle(self, *args: Any, **options: Any) -> None:
        count = max(1, min(int(options["count"]), 1000))
        seed = int(options["seed"])
        revision = max(1, min(int(options["revision"]), 20))
        result = async_to_sync(ingest_source)(
            DemoListingSourceAdapter(),
            SourceSearchRequest(limit=count, seed=seed, revision=revision),
        )
        summary = (
            f"Demo pipeline revision={revision}: received={result.received}, "
            f"created={result.created}, updated={result.updated}, "
            f"unchanged={result.unchanged}, failed={result.failed}"
        )
        if result.failed:
            self.stdout.write(self.style.WARNING(summary))
        else:
            self.stdout.write(self.style.SUCCESS(summary))
