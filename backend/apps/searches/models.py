from __future__ import annotations

import uuid

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class DealType(models.TextChoices):
    RENT = "rent", "Оренда"
    BUY = "buy", "Купівля"


class SearchProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="search_profiles")
    name = models.CharField(max_length=120)
    city = models.CharField(max_length=120, db_index=True)
    deal_type = models.CharField(max_length=16, choices=DealType.choices, default=DealType.RENT)
    price_min = models.PositiveIntegerField(null=True, blank=True)
    price_max = models.PositiveIntegerField(null=True, blank=True)
    currency = models.CharField(max_length=3, default="UAH")
    rooms = models.JSONField(default=list, blank=True)
    desired_districts = models.JSONField(default=list, blank=True)
    excluded_districts = models.JSONField(default=list, blank=True)
    move_in_date = models.DateField(null=True, blank=True)
    occupants = models.PositiveSmallIntegerField(default=1, validators=[MinValueValidator(1), MaxValueValidator(20)])
    children = models.BooleanField(default=False)
    pets = models.JSONField(default=dict, blank=True)
    property_types = models.JSONField(default=list, blank=True)
    filters = models.JSONField(default=dict, blank=True)
    is_active = models.BooleanField(default=True, db_index=True)
    source_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.CheckConstraint(
                condition=models.Q(price_min__isnull=True)
                | models.Q(price_max__isnull=True)
                | models.Q(price_min__lte=models.F("price_max")),
                name="search_price_range_valid",
            )
        ]
        indexes = [models.Index(fields=("user", "is_active"))]

    def __str__(self) -> str:
        return f"{self.name} · {self.city}"


class ImportantPlace(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_profile = models.ForeignKey(SearchProfile, on_delete=models.CASCADE, related_name="important_places")
    name = models.CharField(max_length=160)
    address = models.CharField(max_length=255, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    max_distance_km = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    max_walk_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    max_drive_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    max_transit_minutes = models.PositiveSmallIntegerField(null=True, blank=True)
    importance = models.PositiveSmallIntegerField(default=3, validators=[MinValueValidator(1), MaxValueValidator(5)])
    created_at = models.DateTimeField(auto_now_add=True)


class NotificationPreference(models.Model):
    class Frequency(models.TextChoices):
        INSTANT = "instant", "Миттєво"
        FIFTEEN_MINUTES = "15m", "Кожні 15 хвилин"
        HOURLY = "hourly", "Щогодини"
        TWICE_DAILY = "twice_daily", "Двічі на день"
        DAILY = "daily", "Щодня"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    search_profile = models.OneToOneField(SearchProfile, on_delete=models.CASCADE, related_name="notification_preference")
    frequency = models.CharField(max_length=24, choices=Frequency.choices, default=Frequency.INSTANT)
    min_match_score = models.PositiveSmallIntegerField(default=70, validators=[MinValueValidator(0), MaxValueValidator(100)])
    max_risk_score = models.PositiveSmallIntegerField(default=70, validators=[MinValueValidator(0), MaxValueValidator(100)])
    daily_limit = models.PositiveSmallIntegerField(default=20, validators=[MinValueValidator(1), MaxValueValidator(100)])
    quiet_hours_enabled = models.BooleanField(default=True)
    quiet_hours_start = models.TimeField(default="23:00")
    quiet_hours_end = models.TimeField(default="08:00")
    notify_price_changes = models.BooleanField(default=True)
    notify_reactivated = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
