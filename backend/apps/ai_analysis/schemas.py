from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class SearchCriteriaExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: dict[str, Any] = Field(default_factory=dict)
    confidence: dict[str, float] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list)


class ListingSummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str
    advantages: list[str] = Field(default_factory=list)
    caveats: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)


class OwnerQuestionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[str] = Field(default_factory=list, min_length=1)
    message: str
    confidence: dict[str, float] = Field(default_factory=dict)


class ListingComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listings: list[dict[str, Any]] = Field(default_factory=list)
    recommendation: str
    tradeoffs: list[str] = Field(default_factory=list)
    unknowns: list[str] = Field(default_factory=list)
    confidence: dict[str, float] = Field(default_factory=dict)
