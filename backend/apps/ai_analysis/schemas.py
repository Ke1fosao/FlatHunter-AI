from __future__ import annotations

from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

ConfidenceScore = Annotated[float, Field(ge=0, le=1)]
RoomNumber = Annotated[int, Field(ge=1, le=20)]
ShortText = Annotated[str, Field(min_length=1, max_length=500)]


class ImportantPlaceExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=160)
    max_transit_minutes: int = Field(ge=1, le=240)
    importance: int = Field(ge=1, le=5)


class SearchCriteriaData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=120)
    deal_type: Literal["rent", "buy"] = "rent"
    price_min: int | None = Field(default=None, ge=0)
    price_max: int | None = Field(default=None, ge=0)
    currency: str = Field(default="UAH", min_length=3, max_length=3)
    rooms: list[RoomNumber] = Field(default_factory=list, max_length=20)
    desired_districts: list[str] = Field(default_factory=list, max_length=50)
    excluded_districts: list[str] = Field(default_factory=list, max_length=50)
    occupants: int | None = Field(default=None, ge=1, le=20)
    children: bool | None = None
    pets: dict[str, bool] = Field(default_factory=dict)
    property_types: list[str] = Field(default_factory=list, max_length=20)
    filters: dict[str, Any] = Field(default_factory=dict)
    important_places: list[ImportantPlaceExtraction] = Field(default_factory=list, max_length=10)

    @model_validator(mode="after")
    def validate_price_range(self) -> SearchCriteriaData:
        if self.price_min is not None and self.price_max is not None:
            if self.price_min > self.price_max:
                raise ValueError("price_min must not exceed price_max")
        return self


class SearchCriteriaExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data: SearchCriteriaData = Field(default_factory=SearchCriteriaData)
    confidence: dict[str, ConfidenceScore] = Field(default_factory=dict)
    missing_fields: list[str] = Field(default_factory=list, max_length=30)


class ListingSummaryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    summary: str = Field(min_length=1, max_length=1200)
    advantages: list[ShortText] = Field(default_factory=list, max_length=12)
    caveats: list[ShortText] = Field(default_factory=list, max_length=12)
    unknowns: list[ShortText] = Field(default_factory=list, max_length=12)
    confidence: dict[str, ConfidenceScore] = Field(default_factory=dict)


class OwnerQuestionsResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    questions: list[ShortText] = Field(min_length=1, max_length=12)
    message: str = Field(min_length=1, max_length=1600)
    confidence: dict[str, ConfidenceScore] = Field(default_factory=dict)


class ListingComparisonRow(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str = Field(min_length=1, max_length=80)
    title: str = Field(min_length=1, max_length=240)
    city: str = Field(max_length=120)
    district: str = Field(max_length=120)
    price_uah: int = Field(ge=0)
    price: str = Field(min_length=1, max_length=80)
    rooms: int | None = Field(default=None, ge=1, le=20)
    area: str = Field(max_length=40)
    area_value: float = Field(ge=0)
    floor: str = Field(max_length=40)
    commission: str = Field(max_length=80)
    known_first_payment_uah: int | None = Field(default=None, ge=0)
    pets: str = Field(max_length=80)
    children_allowed: bool | None = None
    building_type: str = Field(max_length=80)
    renovation_level: str = Field(max_length=80)
    heating_type: str = Field(max_length=80)
    backup_power: bool | None = None
    parking: bool | None = None
    match_score: int | None = Field(default=None, ge=0, le=100)
    risk_score: int | None = Field(default=None, ge=0, le=100)
    travel_minutes: int | None = Field(default=None, ge=0, le=1440)
    advantages: list[ShortText] = Field(default_factory=list, max_length=12)
    disadvantages: list[ShortText] = Field(default_factory=list, max_length=12)
    unknowns: list[str] = Field(default_factory=list, max_length=30)


class ListingComparisonResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    listings: list[ListingComparisonRow] = Field(min_length=2, max_length=5)
    recommended_listing_id: str | None = Field(default=None, max_length=80)
    is_decisive: bool = False
    recommendation: str = Field(min_length=1, max_length=1600)
    tradeoffs: list[ShortText] = Field(default_factory=list, max_length=12)
    unknowns: list[str] = Field(default_factory=list, max_length=50)
    confidence: dict[str, ConfidenceScore] = Field(default_factory=dict)
