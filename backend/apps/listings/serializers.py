from rest_framework import serializers

from apps.listings.models import Listing


class ListingFilterSerializer(serializers.Serializer):
    city = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    district = serializers.CharField(required=False, max_length=120, trim_whitespace=True)
    rooms = serializers.IntegerField(required=False, min_value=1, max_value=20)
    price_min = serializers.IntegerField(required=False, min_value=0)
    price_max = serializers.IntegerField(required=False, min_value=0)

    def validate(self, attrs: dict[str, object]) -> dict[str, object]:
        price_min = attrs.get("price_min")
        price_max = attrs.get("price_max")
        if isinstance(price_min, int) and isinstance(price_max, int) and price_min > price_max:
            raise serializers.ValidationError({"price_max": "Must be greater than price_min."})
        return attrs


class ListingSerializer(serializers.ModelSerializer):
    source_code = serializers.CharField(source="source.code", read_only=True)
    source_name = serializers.CharField(source="source.display_name", read_only=True)
    is_demo = serializers.SerializerMethodField()

    class Meta:
        model = Listing
        fields = (
            "id",
            "source_code",
            "source_name",
            "external_id",
            "source_url",
            "title",
            "description",
            "city",
            "district",
            "street",
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
        )

    def get_is_demo(self, instance: Listing) -> bool:
        return bool(instance.attributes.get("demo"))
