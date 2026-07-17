from __future__ import annotations

import uuid

from django.db import models
from django.db.models import Q

from apps.listings.models import Listing


class AnalysisStatus(models.TextChoices):
    READY = "ready", "Ready"
    INSUFFICIENT_DATA = "insufficient_data", "Insufficient data"
    STALE = "stale", "Stale"
    FAILED = "failed", "Failed"
    DISABLED = "disabled", "Disabled"


class ConfidenceLabel(models.TextChoices):
    NONE = "none", "None"
    LOW = "low", "Low"
    MEDIUM = "medium", "Medium"
    HIGH = "high", "High"


class RiskLevel(models.TextChoices):
    LOW = "low", "Low risk"
    REVIEW = "review", "Review"
    ELEVATED = "elevated", "Elevated risk"
    INSUFFICIENT_DATA = "insufficient_data", "Insufficient data"


class PriceDirection(models.TextChoices):
    INCREASE = "increase", "Increase"
    DECREASE = "decrease", "Decrease"


class ListingSnapshot(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="analysis_snapshots",
    )
    captured_at = models.DateTimeField(auto_now_add=True, db_index=True)
    content_hash = models.CharField(max_length=64)
    price_uah = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="UAH")
    title_hash = models.CharField(max_length=64)
    description_hash = models.CharField(max_length=64)
    city = models.CharField(max_length=120)
    district = models.CharField(max_length=120, blank=True)
    street = models.CharField(max_length=160, blank=True)
    rooms = models.PositiveSmallIntegerField()
    total_area = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    floors_total = models.PositiveSmallIntegerField(null=True, blank=True)
    building_type = models.CharField(max_length=48, blank=True)
    renovation_level = models.CharField(max_length=48, blank=True)
    heating_type = models.CharField(max_length=48, blank=True)
    pets_allowed = models.BooleanField(null=True, blank=True)
    children_allowed = models.BooleanField(null=True, blank=True)
    commission_percent = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    is_owner = models.BooleanField(null=True, blank=True)
    attributes_summary = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True)
    source_last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-captured_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "content_hash"),
                name="analysis_snapshot_listing_hash_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("listing", "-captured_at"),
                name="analysis_snapshot_latest_idx",
            )
        ]

    def __str__(self) -> str:
        return f"Snapshot {self.listing_id} · {self.captured_at:%Y-%m-%d %H:%M}"


class ListingPriceHistory(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="price_history",
    )
    snapshot = models.OneToOneField(
        ListingSnapshot,
        on_delete=models.CASCADE,
        related_name="price_event",
    )
    previous_price_uah = models.PositiveIntegerField()
    new_price_uah = models.PositiveIntegerField()
    change_amount_uah = models.IntegerField()
    change_percent = models.DecimalField(max_digits=8, decimal_places=2)
    direction = models.CharField(max_length=16, choices=PriceDirection.choices)
    changed_at = models.DateTimeField()
    detected_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ("-changed_at", "-detected_at")
        constraints = [
            models.CheckConstraint(
                condition=~Q(change_amount_uah=0),
                name="analysis_price_change_nonzero",
            )
        ]
        indexes = [
            models.Index(
                fields=("listing", "-changed_at"),
                name="analysis_price_history_idx",
            )
        ]

    def __str__(self) -> str:
        return f"{self.listing_id}: {self.previous_price_uah} → {self.new_price_uah}"


class ListingMarketAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="market_assessments",
    )
    status = models.CharField(
        max_length=24,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.INSUFFICIENT_DATA,
        db_index=True,
    )
    provider = models.CharField(max_length=64, default="local")
    algorithm_version = models.CharField(max_length=32, default="market-v1")
    input_hash = models.CharField(max_length=64)
    median_price_uah = models.PositiveIntegerField(null=True, blank=True)
    q1_price_uah = models.PositiveIntegerField(null=True, blank=True)
    q3_price_uah = models.PositiveIntegerField(null=True, blank=True)
    median_price_per_sqm = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    target_price_per_sqm = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
    )
    deviation_percent = models.DecimalField(
        max_digits=8,
        decimal_places=2,
        null=True,
        blank=True,
    )
    comparable_count = models.PositiveIntegerField(default=0)
    confidence_score = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    confidence_label = models.CharField(
        max_length=16,
        choices=ConfidenceLabel.choices,
        default=ConfidenceLabel.NONE,
    )
    comparable_ids = models.JSONField(default=list, blank=True)
    selection_summary = models.JSONField(default=dict, blank=True)
    explanation = models.TextField(blank=True)
    calculated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-calculated_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "input_hash"),
                name="analysis_market_listing_input_unique",
            ),
            models.CheckConstraint(
                condition=Q(confidence_score__gte=0) & Q(confidence_score__lte=100),
                name="analysis_market_confidence_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("listing", "-calculated_at"),
                name="analysis_market_latest_idx",
            )
        ]

    def __str__(self) -> str:
        return f"Market {self.listing_id} · {self.status}"


class ListingRiskAssessment(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="risk_assessments",
    )
    market_assessment = models.ForeignKey(
        ListingMarketAssessment,
        on_delete=models.SET_NULL,
        related_name="risk_assessments",
        null=True,
        blank=True,
    )
    status = models.CharField(
        max_length=24,
        choices=AnalysisStatus.choices,
        default=AnalysisStatus.INSUFFICIENT_DATA,
        db_index=True,
    )
    score = models.PositiveSmallIntegerField(default=0)
    level = models.CharField(
        max_length=24,
        choices=RiskLevel.choices,
        default=RiskLevel.INSUFFICIENT_DATA,
    )
    signals = models.JSONField(default=list, blank=True)
    protective_signals = models.JSONField(default=list, blank=True)
    summary = models.TextField(blank=True)
    safety_advice = models.TextField(blank=True)
    algorithm_version = models.CharField(max_length=32, default="risk-v1")
    input_hash = models.CharField(max_length=64)
    calculated_at = models.DateTimeField(auto_now_add=True, db_index=True)
    valid_until = models.DateTimeField(null=True, blank=True, db_index=True)
    error_code = models.CharField(max_length=64, blank=True)

    class Meta:
        ordering = ("-calculated_at", "-id")
        constraints = [
            models.UniqueConstraint(
                fields=("listing", "input_hash"),
                name="analysis_risk_listing_input_unique",
            ),
            models.CheckConstraint(
                condition=Q(score__gte=0) & Q(score__lte=100),
                name="analysis_risk_score_range",
            ),
        ]
        indexes = [
            models.Index(
                fields=("listing", "-calculated_at"),
                name="analysis_risk_latest_idx",
            )
        ]

    def __str__(self) -> str:
        return f"Risk {self.listing_id} · {self.score}"
