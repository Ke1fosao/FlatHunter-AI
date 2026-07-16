from __future__ import annotations

import hashlib
from typing import Any

import aiohttp
from django.conf import settings

from apps.geodata.contracts import (
    GeocodingDisabled,
    GeocodingNotFound,
    GeocodingRequest,
    GeocodingResult,
    GeocodingUnavailable,
)


class DemoGeocodingProvider:
    code = "demo"
    city_centres = {
        "львів": (49.839683, 24.029717),
        "рівне": (50.619900, 26.251617),
        "київ": (50.450100, 30.523400),
    }

    async def geocode(self, request: GeocodingRequest) -> GeocodingResult:
        normalized = request.normalized_query().casefold()
        city_key = next((city for city in self.city_centres if city in normalized), None)
        if city_key is None:
            raise GeocodingNotFound("Demo geocoder supports Львів, Рівне and Київ")

        centre_lat, centre_lon = self.city_centres[city_key]
        digest = hashlib.sha256(normalized.encode("utf-8")).digest()
        lat_offset = ((int.from_bytes(digest[:2], "big") / 65535) - 0.5) * 0.035
        lon_offset = ((int.from_bytes(digest[2:4], "big") / 65535) - 0.5) * 0.05
        return GeocodingResult(
            latitude=round(centre_lat + lat_offset, 6),
            longitude=round(centre_lon + lon_offset, 6),
            display_name=request.normalized_query(),
            provider=self.code,
            confidence=0.96,
            country_code="UA",
        )


class NominatimGeocodingProvider:
    code = "nominatim"
    endpoint = "https://nominatim.openstreetmap.org/search"

    async def geocode(self, request: GeocodingRequest) -> GeocodingResult:
        if not settings.GEOCODING_EXTERNAL_ENABLED:
            raise GeocodingDisabled("External geocoding is disabled")
        timeout = aiohttp.ClientTimeout(total=settings.GEOCODING_TIMEOUT_SECONDS)
        params = {
            "q": request.normalized_query(),
            "format": "jsonv2",
            "limit": "1",
            "addressdetails": "1",
            "countrycodes": request.country_code.casefold(),
        }
        headers = {"User-Agent": settings.GEOCODING_USER_AGENT}
        try:
            async with (
                aiohttp.ClientSession(timeout=timeout, headers=headers) as session,
                session.get(self.endpoint, params=params) as response,
            ):
                if response.status != 200:
                    raise GeocodingUnavailable(f"Nominatim returned HTTP {response.status}")
                payload = await response.json()
        except (aiohttp.ClientError, TimeoutError) as error:
            raise GeocodingUnavailable("Geocoding provider is unavailable") from error

        if not isinstance(payload, list) or not payload:
            raise GeocodingNotFound("Address was not found")
        item = payload[0]
        if not isinstance(item, dict):
            raise GeocodingUnavailable("Geocoding provider returned an invalid response")
        return self._parse_result(item)

    def _parse_result(self, item: dict[str, Any]) -> GeocodingResult:
        try:
            latitude = float(item["lat"])
            longitude = float(item["lon"])
        except (KeyError, TypeError, ValueError) as error:
            raise GeocodingUnavailable("Geocoding result has invalid coordinates") from error
        address = item.get("address") if isinstance(item.get("address"), dict) else {}
        country_code = str(address.get("country_code", "UA")).upper()
        if country_code != "UA":
            raise GeocodingNotFound("Address is outside Ukraine")
        try:
            importance = float(item.get("importance", 0.7))
        except (TypeError, ValueError) as error:
            raise GeocodingUnavailable("Geocoding result has invalid confidence") from error
        confidence = max(0.0, min(importance, 1.0))
        return GeocodingResult(
            latitude=latitude,
            longitude=longitude,
            display_name=str(item.get("display_name", "")),
            provider=self.code,
            confidence=confidence,
            country_code=country_code,
        )
