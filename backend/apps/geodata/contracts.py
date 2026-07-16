from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GeocodingRequest:
    query: str
    city: str = ""
    country_code: str = "UA"

    def normalized_query(self) -> str:
        parts = [self.query.strip(), self.city.strip(), self.country_code.strip().upper()]
        return ", ".join(part for part in parts if part)


@dataclass(frozen=True)
class GeocodingResult:
    latitude: float
    longitude: float
    display_name: str
    provider: str
    confidence: float
    country_code: str = "UA"


class GeocodingProvider(Protocol):
    code: str

    async def geocode(self, request: GeocodingRequest) -> GeocodingResult: ...


class GeocodingError(RuntimeError):
    code = "geocoding_error"


class GeocodingNotFound(GeocodingError):
    code = "geocoding_not_found"


class GeocodingDisabled(GeocodingError):
    code = "geocoding_disabled"


class GeocodingUnavailable(GeocodingError):
    code = "geocoding_unavailable"
