from __future__ import annotations

from decimal import Decimal

from django.test import override_settings

from apps.ai_analysis.models import AIRequest
from apps.ai_analysis.providers import AIProviderError, AIUsage
from apps.ai_analysis.services import parse_search_with_ai


class FlakySearchProvider:
    provider_name = "flaky"
    model_name = "flaky-v1"
    last_usage = AIUsage()

    def __init__(self) -> None:
        self.calls = 0

    async def structured_completion(self, task, schema, context):
        self.calls += 1
        if self.calls == 1:
            raise AIProviderError("temporary overload")
        return schema.model_validate(
            {
                "data": {
                    "deal_type": "rent",
                    "currency": "UAH",
                    "city": "Львів",
                    "rooms": [1],
                    "price_max": 18000,
                    "filters": {},
                },
                "confidence": {"city": 0.98, "rooms": 0.97, "price_max": 0.96},
                "missing_fields": [],
            }
        )


class MeteredSearchProvider(FlakySearchProvider):
    provider_name = "metered"
    model_name = "metered-v1"

    def __init__(self) -> None:
        super().__init__()
        self.last_usage = AIUsage(
            prompt_tokens=120,
            completion_tokens=45,
            estimated_cost_usd=Decimal("0.001230"),
        )

    async def structured_completion(self, task, schema, context):
        self.calls += 1
        return schema.model_validate(
            {
                "data": {
                    "deal_type": "rent",
                    "currency": "UAH",
                    "city": "Львів",
                    "rooms": [1],
                    "price_max": 18000,
                    "filters": {},
                },
                "confidence": {"city": 0.98, "rooms": 0.97, "price_max": 0.96},
                "missing_fields": [],
            }
        )


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="flaky",
    AI_MODEL="flaky-v1",
    AI_MAX_RETRIES=1,
    AI_CACHE_SECONDS=0,
)
def test_provider_retries_once_then_returns_validated_success(db, monkeypatch):
    provider = FlakySearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)

    result = parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    assert result.meta["status"] == "success"
    assert result.meta["attempts"] == 2
    assert provider.calls == 2
    assert AIRequest.objects.get().status == "success"


@override_settings(
    AI_ENABLED=True,
    AI_PROVIDER="metered",
    AI_MODEL="metered-v1",
    AI_MAX_RETRIES=0,
    AI_CACHE_SECONDS=0,
)
def test_provider_token_and_cost_usage_is_persisted(db, monkeypatch):
    provider = MeteredSearchProvider()
    monkeypatch.setattr("apps.ai_analysis.services.get_ai_provider", lambda: provider)

    parse_search_with_ai("Шукаю однокімнатну квартиру у Львові до 18000 грн.")

    audit = AIRequest.objects.get()
    assert audit.prompt_tokens == 120
    assert audit.completion_tokens == 45
    assert audit.total_tokens == 165
    assert audit.estimated_cost_usd == Decimal("0.001230")
