from __future__ import annotations

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, time as datetime_time
from decimal import Decimal, InvalidOperation
from typing import Any

from asgiref.sync import async_to_sync
from django.conf import settings
from django.core.cache import cache
from django.db.models import Sum
from django.utils import timezone
from pydantic import BaseModel, ValidationError

from apps.accounts.models import User
from apps.ai_analysis.models import AIPromptVersion, AIRequest, AIRequestStatus
from apps.ai_analysis.providers import AIProvider, AIProviderError, AIUsage, get_ai_provider
from apps.ai_analysis.rules import (
    build_listing_comparison,
    build_listing_summary,
    build_owner_questions,
    build_search_extraction,
)
from apps.ai_analysis.schemas import (
    ListingComparisonResult,
    ListingSummaryResult,
    OwnerQuestionsResult,
    SearchCriteriaExtraction,
)
from apps.listings.models import Listing
from apps.matching.engine import evaluate_match
from apps.searches.models import SearchProfile

SEARCH_PARSE_FEATURE = "search.parse_natural_language"
LISTING_SUMMARY_FEATURE = "listing.summary"
OWNER_QUESTIONS_FEATURE = "listing.owner_questions"
LISTINGS_COMPARE_FEATURE = "listings.compare"
SEARCH_PARSE_PROMPT_VERSION = "search-parse-v2"
LISTING_SUMMARY_PROMPT_VERSION = "listing-summary-v2"
OWNER_QUESTIONS_PROMPT_VERSION = "owner-questions-v2"
LISTINGS_COMPARE_PROMPT_VERSION = "listings-compare-v2"


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
        payload = SearchCriteriaExtraction.model_validate(_parse_search_payload(text)).model_dump()
        return AIParsedSearch(
            data=payload["data"],
            confidence=payload["confidence"],
            missing_fields=payload["missing_fields"],
            meta=_meta(
                SEARCH_PARSE_FEATURE,
                "deterministic",
                "rules-v2",
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


def owner_questions_with_ai(
    listing: Listing,
    user: User | None = None,
    profile: SearchProfile | None = None,
) -> AIResult:
    profile_data = search_profile_context(profile) if profile is not None else {}
    context = {"listing": listing_context(listing), "profile": profile_data}
    return _run_structured_task(
        feature=OWNER_QUESTIONS_FEATURE,
        schema=OwnerQuestionsResult,
        context=context,
        user=user,
        prompt_version=OWNER_QUESTIONS_PROMPT_VERSION,
        fallback=lambda: build_owner_questions(context["listing"], profile=context["profile"]),
        input_text=f"listing:{listing.id};profile:{profile.id if profile else 'none'}",
    )


def compare_listings_with_ai(
    listings: list[Listing],
    user: User | None = None,
    profile: SearchProfile | None = None,
) -> AIResult:
    contexts = [listing_context(listing, profile=profile) for listing in listings]
    return _run_structured_task(
        feature=LISTINGS_COMPARE_FEATURE,
        schema=ListingComparisonResult,
        context={"listings": contexts, "profile": search_profile_context(profile)},
        user=user,
        prompt_version=LISTINGS_COMPARE_PROMPT_VERSION,
        fallback=lambda: build_listing_comparison(contexts),
        input_text=(
            ",".join(str(listing.id) for listing in listings)
            + f";profile:{profile.id if profile else 'none'}"
        ),
    )


def listing_context(
    listing: Listing,
    profile: SearchProfile | None = None,
) -> dict[str, Any]:
    context: dict[str, Any] = {
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
    if profile is not None:
        match = evaluate_match(profile, listing).to_dict()
        context["match_score"] = int(match["score"])
        context["match_summary"] = str(match["summary"])
        context["match_strengths"] = list(match["strengths"])
        context["match_compromises"] = list(match["compromises"])
        context["match_unknowns"] = list(match["unknowns"])
    return context


def search_profile_context(profile: SearchProfile | None) -> dict[str, Any]:
    if profile is None:
        return {}
    return {
        "id": str(profile.id),
        "name": profile.name,
        "city": profile.city,
        "deal_type": profile.deal_type,
        "price_min": profile.price_min,
        "price_max": profile.price_max,
        "currency": profile.currency,
        "rooms": profile.rooms,
        "desired_districts": profile.desired_districts,
        "excluded_districts": profile.excluded_districts,
        "occupants": profile.occupants,
        "children": profile.children,
        "pets": profile.pets,
        "property_types": profile.property_types,
        "filters": profile.filters,
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
    provider_name = str(getattr(settings, "AI_PROVIDER", "") or "local_rules")
    model_name = str(getattr(settings, "AI_MODEL", "") or "local-rules-v1")

    if not getattr(settings, "AI_ENABLED", False):
        payload = schema.model_validate(fallback()).model_dump()
        return AIResult(
            payload=payload,
            meta=_meta(feature, "deterministic", "rules-v2", prompt_version, "disabled"),
        )

    if _daily_budget_exhausted():
        return _fallback_result(
            schema=schema,
            fallback=fallback,
            user=user,
            feature=feature,
            provider=provider_name,
            model=model_name,
            prompt_version=prompt_version,
            input_summary=input_summary,
            started=started,
            error_message="Daily AI budget exhausted.",
            reason="daily_budget_exhausted",
        )

    try:
        provider = get_ai_provider()
    except AIProviderError as exc:
        return _fallback_result(
            schema=schema,
            fallback=fallback,
            user=user,
            feature=feature,
            provider=provider_name,
            model=model_name,
            prompt_version=prompt_version,
            input_summary=input_summary,
            started=started,
            error_message=str(exc),
            reason="provider_unavailable",
        )

    _register_prompt_version(feature, prompt_version, provider.provider_name, provider.model_name)
    result_cache_key = _result_cache_key(
        feature=feature,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=prompt_version,
        context=context,
    )
    cached_payload = _read_cached_payload(result_cache_key, schema)
    if cached_payload is not None:
        latency_ms = int((time.monotonic() - started) * 1000)
        _write_audit(
            user=user,
            feature=feature,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=prompt_version,
            status=AIRequestStatus.SUCCESS,
            input_summary=input_summary,
            output_data=cached_payload,
            latency_ms=latency_ms,
            cache_key=result_cache_key,
        )
        return AIResult(
            payload=cached_payload,
            meta=_meta(
                feature,
                provider.provider_name,
                provider.model_name,
                prompt_version,
                "cached",
                latency_ms,
                cache_key=result_cache_key,
            ),
        )

    if _circuit_is_open(provider):
        return _fallback_result(
            schema=schema,
            fallback=fallback,
            user=user,
            feature=feature,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=prompt_version,
            input_summary=input_summary,
            started=started,
            error_message="AI provider circuit is open.",
            reason="circuit_open",
            cache_key=result_cache_key,
        )

    try:
        result, attempts = async_to_sync(_call_provider)(provider, feature, schema, context)
        payload = result.model_dump()
    except AIProviderError as exc:
        _record_provider_failure(provider)
        return _fallback_result(
            schema=schema,
            fallback=fallback,
            user=user,
            feature=feature,
            provider=provider.provider_name,
            model=provider.model_name,
            prompt_version=prompt_version,
            input_summary=input_summary,
            started=started,
            error_message=str(exc),
            reason="provider_error",
            cache_key=result_cache_key,
        )

    _record_provider_success(provider)
    _cache_payload(result_cache_key, payload)
    latency_ms = int((time.monotonic() - started) * 1000)
    _write_audit(
        user=user,
        feature=feature,
        provider=provider.provider_name,
        model=provider.model_name,
        prompt_version=prompt_version,
        status=AIRequestStatus.SUCCESS,
        input_summary=input_summary,
        output_data=payload,
        latency_ms=latency_ms,
        cache_key=result_cache_key,
        usage=provider.last_usage,
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
            attempts=attempts,
            cache_key=result_cache_key,
        ),
    )


async def _call_provider(
    provider: AIProvider,
    feature: str,
    schema: type[BaseModel],
    context: dict[str, Any],
) -> tuple[BaseModel, int]:
    timeout_seconds = max(float(getattr(settings, "AI_TIMEOUT_SECONDS", 15)), 0.001)
    max_retries = max(int(getattr(settings, "AI_MAX_RETRIES", 1)), 0)
    attempts = max_retries + 1
    last_error: Exception | None = None

    for attempt in range(1, attempts + 1):
        try:
            raw_result = await asyncio.wait_for(
                provider.structured_completion(feature, schema, context),
                timeout=timeout_seconds,
            )
            validated = schema.model_validate(raw_result.model_dump())
            return validated, attempt
        except Exception as exc:
            last_error = exc
            if attempt < attempts:
                await asyncio.sleep(min(0.05 * (2 ** (attempt - 1)), 0.25))

    if isinstance(last_error, TimeoutError):
        detail = f"timeout after {timeout_seconds:g}s"
    elif last_error is not None:
        detail = f"{type(last_error).__name__}: {last_error}"
    else:
        detail = "unknown provider failure"
    raise AIProviderError(f"AI provider failed after {attempts} attempt(s): {detail}")


def _fallback_result(
    *,
    schema: type[BaseModel],
    fallback: Callable[[], dict[str, Any]],
    user: User | None,
    feature: str,
    provider: str,
    model: str,
    prompt_version: str,
    input_summary: str,
    started: float,
    error_message: str,
    reason: str,
    cache_key: str = "",
) -> AIResult:
    payload = schema.model_validate(fallback()).model_dump()
    latency_ms = int((time.monotonic() - started) * 1000)
    _write_audit(
        user=user,
        feature=feature,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        status=AIRequestStatus.FALLBACK,
        input_summary=input_summary,
        output_data=payload,
        error_message=error_message[:255],
        latency_ms=latency_ms,
        cache_key=cache_key,
    )
    return AIResult(
        payload=payload,
        meta=_meta(
            feature,
            provider,
            model,
            prompt_version,
            "fallback",
            latency_ms,
            reason=reason,
            cache_key=cache_key,
        ),
    )


def _write_audit(
    *,
    user: User | None,
    feature: str,
    provider: str,
    model: str,
    prompt_version: str,
    status: str,
    input_summary: str,
    output_data: dict[str, Any],
    latency_ms: int,
    error_message: str = "",
    cache_key: str = "",
    usage: AIUsage = AIUsage(),
) -> None:
    AIRequest.objects.create(
        user=user,
        feature=feature,
        provider=provider,
        model=model,
        prompt_version=prompt_version,
        status=status,
        input_summary=input_summary,
        output_data=output_data,
        error_message=error_message,
        latency_ms=max(latency_ms, 0),
        prompt_tokens=max(usage.prompt_tokens, 0),
        completion_tokens=max(usage.completion_tokens, 0),
        total_tokens=max(usage.total_tokens, 0),
        estimated_cost_usd=max(usage.estimated_cost_usd, Decimal("0")),
        cache_key=cache_key,
    )


def _parse_search_payload(text: str) -> dict[str, Any]:
    return build_search_extraction(text)


def _meta(
    feature: str,
    provider: str,
    model: str,
    prompt_version: str,
    status: str,
    latency_ms: int | None = None,
    *,
    reason: str | None = None,
    attempts: int | None = None,
    cache_key: str = "",
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
    if reason is not None:
        data["reason"] = reason
    if attempts is not None:
        data["attempts"] = attempts
    if cache_key:
        data["cache_key"] = cache_key
    return data


def _summarize_input(text: str) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest};chars:{len(text)}"


def _result_cache_key(
    *,
    feature: str,
    provider: str,
    model: str,
    prompt_version: str,
    context: dict[str, Any],
) -> str:
    canonical_context = json.dumps(
        context,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    digest = hashlib.sha256(
        f"{feature}|{provider}|{model}|{prompt_version}|{canonical_context}".encode("utf-8")
    ).hexdigest()
    return digest[:64]


def _read_cached_payload(
    cache_key: str,
    schema: type[BaseModel],
) -> dict[str, Any] | None:
    ttl = max(int(getattr(settings, "AI_CACHE_SECONDS", 300)), 0)
    if ttl == 0:
        return None
    stored = cache.get(f"ai:result:{cache_key}")
    if not isinstance(stored, dict):
        return None
    try:
        return schema.model_validate(stored).model_dump()
    except ValidationError:
        cache.delete(f"ai:result:{cache_key}")
        return None


def _cache_payload(cache_key: str, payload: dict[str, Any]) -> None:
    ttl = max(int(getattr(settings, "AI_CACHE_SECONDS", 300)), 0)
    if ttl > 0:
        cache.set(f"ai:result:{cache_key}", payload, timeout=ttl)


def _provider_state_key(provider: AIProvider) -> str:
    identity = f"{provider.provider_name}:{provider.model_name}"
    return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


def _circuit_is_open(provider: AIProvider) -> bool:
    return bool(cache.get(f"ai:circuit:{_provider_state_key(provider)}:open"))


def _record_provider_failure(provider: AIProvider) -> None:
    state_key = _provider_state_key(provider)
    failures_key = f"ai:circuit:{state_key}:failures"
    open_key = f"ai:circuit:{state_key}:open"
    cooldown = max(int(getattr(settings, "AI_CIRCUIT_BREAKER_COOLDOWN_SECONDS", 60)), 1)
    threshold = max(int(getattr(settings, "AI_CIRCUIT_BREAKER_FAILURES", 3)), 1)
    failures = int(cache.get(failures_key, 0)) + 1
    cache.set(failures_key, failures, timeout=cooldown)
    if failures >= threshold:
        cache.set(open_key, True, timeout=cooldown)


def _record_provider_success(provider: AIProvider) -> None:
    state_key = _provider_state_key(provider)
    cache.delete_many(
        [
            f"ai:circuit:{state_key}:failures",
            f"ai:circuit:{state_key}:open",
        ]
    )


def _daily_budget_exhausted() -> bool:
    raw_budget = getattr(settings, "AI_DAILY_BUDGET", 0)
    try:
        budget = Decimal(str(raw_budget))
    except (InvalidOperation, ValueError):
        return False
    if budget <= 0:
        return False

    current_timezone = timezone.get_current_timezone()
    start = timezone.make_aware(
        datetime.combine(timezone.localdate(), datetime_time.min),
        current_timezone,
    )
    spent = AIRequest.objects.filter(
        created_at__gte=start,
        status=AIRequestStatus.SUCCESS,
    ).aggregate(total=Sum("estimated_cost_usd"))["total"] or Decimal("0")
    return bool(spent >= budget)


def _register_prompt_version(
    feature: str,
    prompt_version: str,
    provider: str,
    model: str,
) -> None:
    checksum = hashlib.sha256(f"{feature}:{prompt_version}".encode("utf-8")).hexdigest()
    AIPromptVersion.objects.update_or_create(
        feature=feature,
        version=prompt_version,
        provider=provider,
        defaults={
            "model": model,
            "prompt_checksum": checksum,
            "is_active": True,
        },
    )
    AIPromptVersion.objects.filter(feature=feature, provider=provider).exclude(
        version=prompt_version
    ).update(is_active=False)
