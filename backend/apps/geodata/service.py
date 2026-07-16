from __future__ import annotations

import asyncio
import hashlib
from dataclasses import asdict
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache

from apps.geodata.contracts import (
    GeocodingDisabled,
    GeocodingProvider,
    GeocodingRequest,
    GeocodingResult,
    GeocodingUnavailable,
)
from apps.geodata.providers import DemoGeocodingProvider, NominatimGeocodingProvider


def get_geocoding_provider(name: str | None = None) -> GeocodingProvider:
    provider_name = (name or settings.GEOCODING_PROVIDER).strip().casefold()
    if provider_name == "demo":
        return DemoGeocodingProvider()
    if provider_name == "nominatim":
        if not settings.GEOCODING_EXTERNAL_ENABLED:
            raise GeocodingDisabled("External geocoding is disabled")
        return NominatimGeocodingProvider()
    raise GeocodingDisabled(f"Unsupported geocoding provider: {provider_name}")


def _cache_key(provider: str, request: GeocodingRequest) -> str:
    digest = hashlib.sha256(request.normalized_query().casefold().encode("utf-8")).hexdigest()
    return f"geocoding:{provider}:{digest}"


async def _get_cached(key: str) -> dict[str, Any] | None:
    value = await sync_to_async(cache.get)(key)
    return value if isinstance(value, dict) else None


async def _set_cached(key: str, result: GeocodingResult) -> None:
    await sync_to_async(cache.set)(key, asdict(result), settings.GEOCODING_CACHE_SECONDS)


async def _wait_for_external_slot(provider: str) -> None:
    lock_key = f"geocoding-rate:{provider}"
    for _ in range(10):
        acquired = await sync_to_async(cache.add)(lock_key, "1", timeout=1)
        if acquired:
            return
        await asyncio.sleep(0.12)
    raise GeocodingUnavailable("Geocoding provider rate limit is busy")


async def geocode_address(
    request: GeocodingRequest,
    provider: GeocodingProvider | None = None,
) -> GeocodingResult:
    selected = provider or get_geocoding_provider()
    key = _cache_key(selected.code, request)
    cached = await _get_cached(key)
    if cached is not None:
        return GeocodingResult(**cached)
    if selected.code != "demo":
        await _wait_for_external_slot(selected.code)
    result = await selected.geocode(request)
    await _set_cached(key, result)
    return result
