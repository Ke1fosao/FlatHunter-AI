from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.listings.models import Listing, UserListingState


class ListingFilterSerializer(serializers.Serializer):
    city = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    district = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    rooms = serializers.IntegerField(required=False, min_value=1, max_value=20)
    price_min = serializers.IntegerField(required=False, min_value=0)
    price_max = serializers.IntegerField(required=False, min_value=0)
    favorites = serializers.BooleanField(required=False)
    compared = serializers.BooleanField(required=False)
    include_hidden = serializers.BooleanField(required=False, default=False)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        price_min = attrs.get("price_min")
        price_max = attrs.get("price_max")
        if isinstance(price_min, int) and isinstance(price_max, int) and price_min > price_max:
            raise serializers.ValidationError({"price_max": "Must be greater than price_min."})
        return attrs


class ListingStateMutationSerializer(serializers.Serializer):
    value = serializers.BooleanField()


class ListingUserStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserListingState
        fields = ("is_favorite", "is_hidden", "is_compared", "note", "updated_at")
        read_only_fields = fields


class ListingSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)
    source_name = serializers.CharField(source="source.display_name", read_only=True)
    is_demo = serializers.SerializerMethodField()
    user_state = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id",
            "source_code",
            "source_name",
            "external_id",
            "source_url",
            "canonical_url",
            "title",
            "description",
            "deal_type",
            "property_type",
            "city",
            "district",
            "street",
            "latitude",
            "longitude",
            "location_accuracy",
            "price",
            "price_uah",
            "currency",
            "rooms",
            "total_area",
            "floor",
            "floors_total",
            "building_type",
            "renovation_level",
            "heating_type",
            "pets_allowed",
            "children_allowed",
            "commission_percent",
            "is_owner",
            "images",
            "attributes",
            "published_at",
            "first_seen_at",
            "last_seen_at",
            "is_active",
            "is_demo",
            "user_state",
        )

    def get_is_demo(self, instance: Listing) -> bool:
        return bool(instance.attributes.get("demo"))

    def get_user_state(self, instance: Listing) -> dict[str, Any]:
        states = getattr(instance, "current_user_states", [])
        state = states[0] if states else None
        if state is None:
            return {
                "is_favorite": False,
                "is_hidden": False,
                "is_compared": False,
                "note": "",
                "updated_at": None,
            }
        return ListingUserStateSerializer(state).data
