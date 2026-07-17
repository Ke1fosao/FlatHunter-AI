from __future__ import annotations

import re
from abc import ABC, abstractmethod
from typing import Any

from django.conf import settings
from pydantic import BaseModel

from apps.ai_analysis.rules import (
    build_listing_comparison,
    build_listing_summary,
    build_owner_questions,
)
from apps.searches.parser import parse_search_text


class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a structured task."""


class AIProvider(ABC):
    provider_name: str
    model_name: str

    @abstractmethod
    async def structured_completion(
        self,
        task: str,
        schema: type[BaseModel],
        context: dict[str, Any],
    ) -> BaseModel:
        """Return validated structured output for a bounded AI task."""


class LocalRulesAIProvider(AIProvider):
    provider_name = "local_rules"

    def __init__(self, model_name: str = "local-rules-v1") -> None:
        self.model_name = model_name or "local-rules-v1"

    async def structured_completion(
        self,
        task: str,
        schema: type[BaseModel],
        context: dict[str, Any],
    ) -> BaseModel:
        if task == "listing.summary":
            return schema.model_validate(build_listing_summary(dict(context["listing"])))
        if task == "listing.owner_questions":
            return schema.model_validate(build_owner_questions(dict(context["listing"])))
        if task == "listings.compare":
            listings = [dict(item) for item in context.get("listings", [])]
            return schema.model_validate(build_listing_comparison(listings))
        if task != "search.parse_natural_language":
            raise AIProviderError(f"Unsupported local AI task: {task}")
        text = str(context.get("text", ""))
        parsed = parse_search_text(text)
        data = dict(parsed.data)
        confidence = dict(parsed.confidence)
        self._add_important_places(text, data, confidence)
        missing_fields = [field for field in ("city", "price_max", "rooms") if field not in data]
        return schema.model_validate(
            {
                "data": data,
                "confidence": confidence,
                "missing_fields": missing_fields,
            }
        )

    def _add_important_places(
        self,
        text: str,
        data: dict[str, Any],
        confidence: dict[str, float],
    ) -> None:
        normalized = " ".join(text.lower().split())
        place_name = ""
        if "політех" in normalized:
            place_name = "Львівська політехніка"
        elif "університет" in normalized:
            place_name = "університет"
        elif "робот" in normalized:
            place_name = "робота"

        if not place_name:
            return

        minutes = 30
        match = re.search(r"до\s+(\d{1,3})\s*(?:хв|хвилин)", normalized)
        if match:
            minutes = int(match.group(1))

        data["important_places"] = [
            {
                "name": place_name,
                "max_transit_minutes": minutes,
                "importance": 5 if place_name == "Львівська політехніка" else 4,
            }
        ]
        confidence["important_places.0.name"] = 0.9
        confidence["important_places.0.max_transit_minutes"] = 0.86 if match else 0.55


def get_ai_provider() -> AIProvider:
    provider = getattr(settings, "AI_PROVIDER", "") or "local_rules"
    model = getattr(settings, "AI_MODEL", "") or "local-rules-v1"
    if provider in {"local_rules", "demo", "mock"}:
        return LocalRulesAIProvider(model_name=model)
    raise AIProviderError(f"AI provider '{provider}' is not configured in this build.")
