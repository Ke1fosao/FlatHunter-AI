from rest_framework import serializers

from apps.listings.models import Listing


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
