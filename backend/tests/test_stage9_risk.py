from __future__ import annotations

from decimal import Decimal

import pytest
from django.utils import timezone

from apps.analysis.models import (
    AnalysisStatus,
    ConfidenceLabel,
    ListingMarketAssessment,
    RiskLevel,
)
from apps.analysis.risk import calculate_risk_assessment
from apps.listings.models import Listing, ListingSource


@pytest.fixture
def risk_source(db) -> ListingSource:
    return ListingSource.objects.create(
        code="stage9-risk",
        display_name="Stage 9 Risk",
        enabled=True,
        access_mode="demo",
        legal_status="approved_demo",
    )


def make_risk_listing(
    source: ListingSource,
    external_id: str,
    *,
    description: str,
    is_owner: bool | None = None,
) -> Listing:
    return Listing.objects.create(
        source=source,
        external_id=external_id,
        source_url=f"https://example.invalid/{external_id}",
        canonical_url=f"https://example.invalid/{external_id}",
        title="Оренда квартири у Львові",
        description=description,
        city="Львів",
        district="Франківський",
        street="Наукова",
        price=12000,
        price_uah=12000,
        rooms=1,
        total_area=Decimal("40.00"),
        floor=4,
        floors_total=10,
        commission_percent=Decimal("0.00"),
        is_owner=is_owner,
        published_at=timezone.now(),
        attributes={"demo": True},
    )


def make_market(listing: Listing, deviation: str) -> ListingMarketAssessment:
    return ListingMarketAssessment.objects.create(
        listing=listing,
        status=AnalysisStatus.READY,
        provider="local",
        algorithm_version="market-v1",
        input_hash=(listing.external_id.encode().hex() + "0" * 64)[:64],
        median_price_uah=18000,
        q1_price_uah=16500,
        q3_price_uah=19500,
        deviation_percent=Decimal(deviation),
        comparable_count=24,
        confidence_score=Decimal("82.00"),
        confidence_label=ConfidenceLabel.HIGH,
        comparable_ids=[],
        selection_summary={},
        explanation="Стабільна синтетична вибірка.",
    )


def test_high_severity_evidence_is_explainable_and_safely_worded(risk_source):
    listing = make_risk_listing(
        risk_source,
        "risk-high",
        description=(
            "Для бронювання потрібна передоплата до перегляду. Переказати кошти можна "
            "за посиланням https://payments.example.invalid."
        ),
    )
    result = calculate_risk_assessment(listing, make_market(listing, "-36.00"))

    assert result.status == AnalysisStatus.READY
    assert result.level == RiskLevel.ELEVATED
    assert result.score >= 50
    assert {signal.code for signal in result.signals} >= {
        "price_far_below_market",
        "prepayment_language",
        "external_links_in_description",
    }
    for signal in result.signals:
        assert signal.code
        assert signal.weight > 0
        assert signal.severity
        assert signal.evidence is not None
        assert signal.label
        assert signal.recommendation
    combined = " ".join(
        [result.summary, result.safety_advice]
        + [signal.label for signal in result.signals]
        + [signal.recommendation for signal in result.signals]
    ).casefold()
    assert "шахрай" not in combined
    assert "fraud" not in combined
    assert "не є юридичним висновком" in result.safety_advice


def test_detailed_owner_listing_remains_low_risk(risk_source):
    listing = make_risk_listing(
        risk_source,
        "risk-low",
        is_owner=True,
        description=(
            "Довгострокова оренда квартири. Указано площу, поверх, район, стан ремонту, "
            "умови договору, комунальні платежі, можливість перегляду та повний перелік "
            "платежів. Це синтетичний опис для тестування без реальної адреси або контакту. "
            "Перегляд за попередньою домовленістю, оплата лише після перевірки документів."
        ),
    )
    result = calculate_risk_assessment(listing, make_market(listing, "-4.00"))

    assert result.status == AnalysisStatus.READY
    assert result.level == RiskLevel.LOW
    assert result.score < 25
    assert any(signal.code == "owner_declared" for signal in result.protective_signals)
