from __future__ import annotations

from rest_framework import serializers


class ListingComparisonRequestSerializer(serializers.Serializer):
    listing_ids = serializers.ListField(
        child=serializers.UUIDField(),
        min_length=2,
        max_length=5,
        allow_empty=False,
    )

    def validate_listing_ids(self, value: list[object]) -> list[object]:
        if len(set(value)) != len(value):
            raise serializers.ValidationError("Listing IDs must be unique.")
        return value
