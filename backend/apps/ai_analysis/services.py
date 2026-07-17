from __future__ import annotations

import hashlib
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings
from pydantic import BaseModel, ValidationError

from apps.accounts.models import User
from apps.ai_analysis.models import AIRequest, AIRequestStatus
from apps.ai_analysis.providers import AIProviderError, get_ai_provider
from apps.ai_analysis.rules import (
    build_listing_comparison,
    build_listing_summary,
    build_owner_questions,
)
from apps.ai_analysis.schemas import (
    ListingComparisonResult,
    ListingSummaryResult,
    OwnerQuestionsResult,
    SearchCriteriaExtraction,
)
from apps.listings.models import Listing
from apps.searches.parser import ParsedSearch, parse_search_text

SEARCH_PARSE_FEATURE = "search.parse_natural_language"
LISTING_SUMMARY_FEATURE = "listing.summary"
OWNER_QUESTIONS_FEATURE = "listing.owner_questions"
LISTINGS_COMPARE_FEATURE = "listings.compare"
SEARCH_PARSE_PROMPT_VERSION = "search-parse-v1"
LISTING_SUMMARY_PROMPT_VERSION = "listing-summary-v1"
OWNER_QUESTIONS_PROMPT_VERSION = "owner-questions-v1"
LISTINGS_COMPARE_PROMPT_VERSION = "listings-compare-v1"


@dataclass(frozen=True)
class AIParsedSearch:
    data: dict[str, Any]
    confidence: dict[str, float]
    missing_fields: list[str]
    meta: dict[str, Any]


@dataclass(frozen=True)
class AIResult:
    payload: dict[str, Any]
    meta: dict[str, Any]


def parse_search_with_ai(text: str, user: User | None = None) -> AIParsedSearch:
    if not getattr(settings, "AI_ENABLED", False):
        parsed = parse_search_text(text)
        return _from_parsed_search(
            parsed,
            _meta(
                SEARCH_PARSE_FEATURE,
                "deterministic",
                "rules-v1",
                SEARCH_PARSE_PROMPT_VERSION,
                "disabled",
            ),
        )

    result = _run_structured_task(
        feature=SEARCH_PARSE_FEATURE,
        schema=SearchCriteriaExtraction,
        context={"text": text},
        user=user,
        prompt_version=SEARCH_PARSE_PROMPT_VERSION,
        fallback=lambda: _parse_search_payload(text),
        input_text=text,
    )
    return AIParsedSearch(
        data=result.payload["data"],
        confidence=result.payload["confidence"],
        missing_fields=result.payload["missing_fields"],
        meta=result.meta,
    )


def summarize_listing_with_ai(listing: Listing, user: User | None = None) -> AIResult:
    context = {"listing": listing_context(listing)}
    return _run_structured_task(
        feature=LISTING_SUMMARY_FEATURE,
        schema=ListingSummaryResult,
        context=context,
        user=user,
        prompt_version=LISTING_SUMMARY_PROMPT_VERSION,
        fallback=lambda: build_listing_summary(context["listing"]),
        input_text=f"listing:{listing.id}",
    )


def owner_questions_with_ai(listing: Listing, user: User | None = None) -> AIResult:
    context = {"listing": listing_context(listing)}
    return _run_structured_task(
        feature=OWNER_QUESTIONS_FEATURE,
        schema=OwnerQuestionsResult,
        context=context,
        user=user,
        prompt_version=OWNER_QUESTIONS_PROMPT_VERSION,
        fallback=lambda: build_owner_questions(context["listing"]),
        input_text=f"listing:{listing.id}",
    )


def compare_listings_with_ai(listings: list[Listing], user: User | None = None) -> AIResult:
    contexts = [listing_context(listing) for listing in listings]
    return _run_structured_task(
        feature=LISTINGS_COMPARE_FEATURE,
        schema=ListingComparisonResult,
        context={"listings": contexts},
        user=user,
        prompt_version=LISTINGS_COMPARE_PROMPT_VERSION,
        fallback=lambda: build_listing_comparison(contexts),
        input_text=",".join(str(listing.id) for listing in listings),
    )


def listing_context(listing: Listing) -> dict[str, Any]:
    return {
        "id": str(listing.id),
        "title": listing.title,
        "description": listing.description,
        "city": listing.city,
        "district": listing.district,
        "street": listing.street,
        "price_uah": listing.price_uah,
        "rooms": listing.rooms,
        "total_area": str(listing.total_area) if listing.total_area is not None else "",
        "floor": listing.floor,
        "floors_total": listing.floors_total,
        "building_type": listing.building_type,
        "renovation_level": listing.renovation_level,
        "heating_type": listing.heating_type,
        "pets_allowed": listing.pets_allowed,
        "children_allowed": listing.children_allowed,
        "commission_percent": (
            str(listing.commission_percent) if listing.commission_percent is not None else ""
        ),
        "is_owner": listing.is_owner,
        "published_at": listing.published_at.isoformat(),
        "attributes": listing.attributes,
    }


def _run_structured_task(
    *,
    feature: str,
    schema: type[BaseModel],
    context: dict[str, Any],
    user: User | None,
    prompt_version: str,
    fallback: Callable[[], dict[str, Any]],
    input_text: str,
) -> AIResult:
    started = time.monotonic()
    input_summary = _summarize_input(input_text)

    if not getattr(settings, "AI_ENABLED", False):
        payload = schema.model_validate(fallback()).model_dump()
        return AIResult(
            payload=payload,
            meta=_meta(feature, "deterministic", "rules-v1", prompt_version, "disabled"),
        )

    try:
        provider = get_ai_provider()
        result = async_to_sync(provider.structured_completion)(feature, schema, context)
        latency_ms = int((time.monotonic() - started) * 1000)
        payload = result.model_dump()
        AIRequest.objects.create(
            user=user,
            feature=feature,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=prompt_version,
            status=AIRequestStatus.SUCCESS,
            input_summary=input_summary,
            output_data=payload,
            latency_ms=latency_ms,
        )
        return AIResult(
            payload=payload,
            meta=_meta(
                feature,
                provider.provider_name,
                provider.model_name,
                prompt_version,
                "success",
                latency_ms,
            ),
        )
    except (AIProviderError, ValidationError, KeyError, TypeError, ValueError) as exc:
        latency_ms = int((time.monotonic() - started) * 1000)
        provider_name = getattr(settings, "AI_PROVIDER", "") or "unknown"
        model_name = getattr(settings, "AI_MODEL", "")
        payload = schema.model_validate(fallback()).model_dump()
        AIRequest.objects.create(
            user=user,
            feature=feature,
            provider=provider_name,
            model=model_name,
            prompt_version=prompt_version,
            status=AIRequestStatus.FALLBACK,
            input_summary=input_summary,
            output_data=payload,
            error_message=str(exc)[:255],
            latency_ms=latency_ms,
        )
        return AIResult(
            payload=payload,
            meta=_meta(feature, provider_name, model_name, prompt_version, "fallback", latency_ms),
        )


def _parse_search_payload(text: str) -> dict[str, Any]:
    parsed = parse_search_text(text)
    return {
        "data": parsed.data,
        "confidence": parsed.confidence,
        "missing_fields": parsed.missing_fields,
    }


def _from_parsed_search(parsed: ParsedSearch, meta: dict[str, Any]) -> AIParsedSearch:
    return AIParsedSearch(
        data=parsed.data,
        confidence=parsed.confidence,
        missing_fields=parsed.missing_fields,
        meta=meta,
    )


def _meta(
    feature: str,
    provider: str,
    model: str,
    prompt_version: str,
    status: str,
    latency_ms: int | None = None,
) -> dict[str, Any]:
    data: dict[str, Any] = {
        "feature": feature,
        "provider": provider,
        "model": model,
        "prompt_version": prompt_version,
        "status": status,
    }
    if latency_ms is not None:
        data["latency_ms"] = latency_ms
    return data


def _summarize_input(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest};chars:{len(text)}"
