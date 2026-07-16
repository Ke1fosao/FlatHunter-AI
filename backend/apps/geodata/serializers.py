from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from rest_framework import serializers

from apps.geodata.spatial import BoundingBox, BoundingBoxValidationError
from apps.listings.serializers import OptionalQueryBooleanField
from apps.searches.models import ImportantPlace


class MapListingQuerySerializer(serializers.Serializer):
    profile_id = serializers.UUIDField(required=False)
    bbox = serializers.CharField(required=False, max_length=200)
    min_score = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100)
    favorites = OptionalQueryBooleanField(required=False)
    limit = serializers.IntegerField(required=False, default=300, min_value=1, max_value=500)

    def validate_bbox(self, value: str) -> BoundingBox:
        try:
            return BoundingBox.parse(value)
        except BoundingBoxValidationError as error:
            raise serializers.ValidationError(str(error)) from error


class ImportantPlaceSerializer(serializers.ModelSerializer):
    latitude = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-90"),
        max_value=Decimal("90"),
    )
    longitude = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=9,
        decimal_places=6,
        min_value=Decimal("-180"),
        max_value=Decimal("180"),
    )
    max_distance_km = serializers.DecimalField(
        required=False,
        allow_null=True,
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0.10"),
        max_value=Decimal("100.00"),
    )

    class Meta:
        model = ImportantPlace
        fields = (
            "id",
            "name",
            "address",
            "latitude",
            "longitude",
            "geocoding_provider",
            "geocoding_confidence",
            "max_distance_km",
            "max_walk_minutes",
            "max_drive_minutes",
            "max_transit_minutes",
            "importance",
            "created_at",
        )
        read_only_fields = (
            "id",
            "geocoding_provider",
            "geocoding_confidence",
            "created_at",
        )

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        latitude = attrs.get("latitude")
        longitude = attrs.get("longitude")
        if (latitude is None) != (longitude is None):
            raise serializers.ValidationError(
                {"latitude": "Latitude and longitude must be provided together."}
            )
        if latitude is None and not str(attrs.get("address", "")).strip():
            raise serializers.ValidationError(
                {"address": "Provide an address or map coordinates."}
            )
        return attrs


class GeocodingPreviewSerializer(serializers.Serializer):
    address = serializers.CharField(max_length=255, trim_whitespace=True)
    city = serializers.CharField(required=False, max_length=120, trim_whitespace=True)


class MapContextQuerySerializer(serializers.Serializer):
    listing_ids = serializers.CharField(required=False, allow_blank=True, max_length=4000)

    def validate_listing_ids(self, value: str) -> list[UUID]:
        if not value.strip():
            return []
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if len(parts) > 100:
            raise serializers.ValidationError("At most 100 listing IDs are allowed.")
        try:
            return [UUID(part) for part in parts]
        except ValueError as error:
            raise serializers.ValidationError("listing_ids must contain UUID values.") from error
