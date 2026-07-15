from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SourceHealth:
    healthy: bool
    message: str


@dataclass(frozen=True)
class SourceSearchRequest:
    limit: int = 150
    seed: int = 20260716


@dataclass(frozen=True)
class NormalizedListingData:
    external_id: str
    values: dict[str, Any]


class ListingSourceAdapter(ABC):
    source_code: str
    display_name: str

    @abstractmethod
    async def health_check(self) -> SourceHealth: ...

    @abstractmethod
    async def search(self, request: SourceSearchRequest) -> list[dict[str, Any]]: ...

    @abstractmethod
    async def fetch_details(self, external_id: str) -> dict[str, Any]: ...

    @abstractmethod
    async def normalize(self, raw_listing: dict[str, Any]) -> NormalizedListingData: ...
