from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from apps.listings.models import SourceAccessMode


@dataclass(frozen=True)
class SourceHealth:
    healthy: bool
    message: str


@dataclass(frozen=True)
class SourceSearchRequest:
    limit: int = 150
    seed: int = 20260716
    revision: int = 1

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= 1000:
            raise ValueError("limit must be between 1 and 1000")
        if not 1 <= self.revision <= 20:
            raise ValueError("revision must be between 1 and 20")


@dataclass(frozen=True)
class NormalizedListingData:
    external_id: str
    values: dict[str, Any]


class ListingSourceAdapter(ABC):
    source_code: str
    display_name: str
    access_mode: str = SourceAccessMode.DEMO
    legal_status: str = "approved_demo"

    def external_id_from_raw(self, raw_listing: dict[str, Any]) -> str:
        external_id = str(raw_listing.get("external_id", "")).strip()
        if not external_id:
            raise ValueError("raw listing has no external_id")
        return external_id

    @abstractmethod
    async def health_check(self) -> SourceHealth: ...

    @abstractmethod
    async def search(self, request: SourceSearchRequest) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def fetch_details(self, external_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def normalize(self, raw_listing: dict[str, Any]) -> NormalizedListingData: ...
