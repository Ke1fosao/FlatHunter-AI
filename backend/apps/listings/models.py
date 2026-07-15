from __future__ import annotations

import uuid

from django.db import models


class SourceAccessMode(models.TextChoices):
    DEMO = "demo", "Synthetic demo"
    API = "api", "Official API"
    FEED = "feed", "Official feed"
    MANUAL = "manual", "Manual import"


class ListingSource(models.Model):
    code = models.SlugField(primary_key=True, max_length=48)
    display_name = models.CharField(max_length=120)
    enabled = models.BooleanField(default=False, db_index=True)
    access_mode = models.CharField(max_length=16, choices=SourceAccessMode.choices)
    legal_status = models.CharField(max_length=32, default="approved_demo")
    terms_checked_at = models.DateTimeField(null=True, blank=True)
    rate_limit = models.PositiveIntegerField(default=60)
    request_interval = models.DecimalField(max_digits=6, decimal_places=2, default=1)
    supports_search = models.BooleanField(default=True)
    supports_details = models.BooleanField(default=True)
    supports_contacts = models.BooleanField(default=False)
    supports_images = models.BooleanField(default=True)
    requires_authentication = models.BooleanField(default=False)
    last_success_at = models.DateTimeField(null=True, blank=True)
    last_error_at = models.DateTimeField(null=True, blank=True)
    health_status = models.CharField(max_length=24, default="unknown")

    class Meta:
        ordering = ("display_name",)

    def __str__(self) -> str:
        return self.display_name


class RawListing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        ListingSource,
        on_delete=models.PROTECT,
        related_name="raw_listings",
    )
    external_id = models.CharField(max_length=128)
    payload = models.JSONField()
    payload_hash = models.CharField(max_length=64, db_index=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    normalized_at = models.DateTimeField(null=True, blank=True)
    normalization_error = models.TextField(blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_id", "payload_hash"),
                name="raw_listing_payload_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("source", "external_id"),
                name="raw_source_external_idx",
            )
        ]


class Listing(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    source = models.ForeignKey(
        ListingSource,
        on_delete=models.PROTECT,
        related_name="listings",
    )
    raw_listing = models.OneToOneField(
        RawListing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="listing",
    )
    external_id = models.CharField(max_length=128)
    source_url = models.URLField(max_length=500)
    canonical_url = models.URLField(max_length=500)
    title = models.CharField(max_length=240)
    description = models.TextField(blank=True)
    deal_type = models.CharField(max_length=16, default="rent")
    property_type = models.CharField(max_length=32, default="apartment")
    country = models.CharField(max_length=2, default="UA")
    region = models.CharField(max_length=120, blank=True)
    city = models.CharField(max_length=120, db_index=True)
    district = models.CharField(max_length=120, blank=True, db_index=True)
    street = models.CharField(max_length=160, blank=True)
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    location_accuracy = models.CharField(max_length=24, default="district")
    price = models.PositiveIntegerField(db_index=True)
    currency = models.CharField(max_length=3, default="UAH")
    price_uah = models.PositiveIntegerField(db_index=True)
    rooms = models.PositiveSmallIntegerField(db_index=True)
    total_area = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
    )
    floor = models.PositiveSmallIntegerField(null=True, blank=True)
    floors_total = models.PositiveSmallIntegerField(null=True, blank=True)
    building_type = models.CharField(max_length=48, blank=True)
    renovation_level = models.CharField(max_length=48, blank=True)
    heating_type = models.CharField(max_length=48, blank=True)
    pets_allowed = models.BooleanField(null=True, blank=True)
    children_allowed = models.BooleanField(null=True, blank=True)
    commission_percent = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        null=True,
        blank=True,
    )
    is_owner = models.BooleanField(null=True, blank=True)
    images = models.JSONField(default=list, blank=True)
    attributes = models.JSONField(default=dict, blank=True)
    published_at = models.DateTimeField(db_index=True)
    first_seen_at = models.DateTimeField(auto_now_add=True)
    last_seen_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    normalization_version = models.PositiveSmallIntegerField(default=1)

    class Meta:
        ordering = ("-published_at", "-first_seen_at")
        constraints = [
            models.UniqueConstraint(
                fields=("source", "external_id"),
                name="listing_source_external_unique",
            )
        ]
        indexes = [
            models.Index(
                fields=("is_active", "city", "-published_at"),
                name="listing_active_city_pub_idx",
            ),
            models.Index(
                fields=("city", "rooms", "price_uah"),
                name="listing_city_rooms_price_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} · {self.price_uah} грн"
