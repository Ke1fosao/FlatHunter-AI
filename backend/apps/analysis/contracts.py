from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from apps.listings.models import Listing


@dataclass(frozen=True)
class ComparableListing:
    id: UUID
    price_uah: int
    total_area: Decimal | None
    city: str
    district: str
    building_type: str
    renovation_level: str
    location_accuracy: str
    published_at: datetime
    selection_stage: str


@dataclass(frozen=True)
class ComparableSet:
    items: tuple[ComparableListing, ...]
    selection_stage: str
    candidate_count: int
    excluded_same_cluster: int = 0
    limit_applied: bool = False

    @property
    def ids(self) -> tuple[UUID, ...]:
        return tuple(item.id for item in self.items)


@dataclass(frozen=True)
class MarketAssessmentResult:
    status: str
    median_price_uah: int | None
    q1_price_uah: int | None
    q3_price_uah: int | None
    median_price_per_sqm: Decimal | None
    target_price_per_sqm: Decimal | None
    deviation_percent: Decimal | None
    comparable_count: int
    confidence_score: Decimal
    confidence_label: str
    comparable_ids: tuple[UUID, ...]
    selection_summary: dict[str, object]
    explanation: str


@dataclass(frozen=True)
class RiskSignal:
    code: str
    weight: int
    severity: str
    evidence: dict[str, object]
    label: str
    recommendation: str

    def to_dict(self) -> dict[str, object]:
        return {
            "code": self.code,
            "weight": self.weight,
            "severity": self.severity,
            "evidence": self.evidence,
            "label": self.label,
            "recommendation": self.recommendation,
        }


@dataclass(frozen=True)
class RiskAssessmentResult:
    status: str
    score: int
    level: str
    signals: tuple[RiskSignal, ...] = field(default_factory=tuple)
    protective_signals: tuple[RiskSignal, ...] = field(default_factory=tuple)
    summary: str = ""
    safety_advice: str = ""


class MarketAnalysisProvider(Protocol):
    provider_name: str
    model_version: str

    def select_comparables(self, listing: Listing) -> ComparableSet: ...

    def assess(self, listing: Listing, comparables: ComparableSet) -> MarketAssessmentResult: ...
