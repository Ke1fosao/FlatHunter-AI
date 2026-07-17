from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from django.conf import settings
from pydantic import BaseModel

from apps.ai_analysis.rules import (
    build_listing_comparison,
    build_listing_summary,
    build_owner_questions,
    build_search_extraction,
)


class AIProviderError(Exception):
    """Raised when an AI provider cannot complete a structured task."""


@dataclass(frozen=True)
class AIUsage:
    prompt_tokens: int = 0
    completion_tokens: int = 0
    estimated_cost_usd: Decimal = Decimal("0")

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens


class AIProvider(ABC):
    provider_name: str
    model_name: str
    last_usage: AIUsage = AIUsage()

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
        self.last_usage = AIUsage()

    async def structured_completion(
        self,
        task: str,
        schema: type[BaseModel],
        context: dict[str, Any],
    ) -> BaseModel:
        if task == "listing.summary":
            return schema.model_validate(build_listing_summary(dict(context["listing"])))
        if task == "listing.owner_questions":
            profile = dict(context.get("profile") or {})
            return schema.model_validate(
                build_owner_questions(dict(context["listing"]), profile=profile)
            )
        if task == "listings.compare":
            listings = [dict(item) for item in context.get("listings", [])]
            return schema.model_validate(build_listing_comparison(listings))
        if task == "search.parse_natural_language":
            return schema.model_validate(build_search_extraction(str(context.get("text", ""))))
        raise AIProviderError(f"Unsupported local AI task: {task}")


def get_ai_provider() -> AIProvider:
    provider = getattr(settings, "AI_PROVIDER", "") or "local_rules"
    model = getattr(settings, "AI_MODEL", "") or "local-rules-v1"
    if provider in {"local_rules", "demo", "mock"}:
        return LocalRulesAIProvider(model_name=model)
    raise AIProviderError(f"AI provider '{provider}' is not configured in this build.")
