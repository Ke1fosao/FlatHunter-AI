from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from apps.searches.models import ImportantPlace, NotificationPreference, SearchProfile


class ImportantPlaceSerializer(serializers.ModelSerializer):
    class Meta:
        model = ImportantPlace
        exclude = ("search_profile",)
        read_only_fields = ("id", "created_at")


class NotificationPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationPreference
        exclude = ("search_profile",)
        read_only_fields = ("id", "updated_at")


class SearchProfileSerializer(serializers.ModelSerializer):
    important_places = ImportantPlaceSerializer(many=True, required=False)
    notification_preference = NotificationPreferenceSerializer(required=False)

    class Meta:
        model = SearchProfile
        exclude = ("user",)
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        price_min = attrs.get("price_min", getattr(self.instance, "price_min", None))
        price_max = attrs.get("price_max", getattr(self.instance, "price_max", None))
        if price_min is not None and price_max is not None and price_min > price_max:
            raise serializers.ValidationError(
                {"price_max": "Максимальна ціна має бути не меншою за мінімальну."}
            )
        return attrs

    def create(self, validated_data: dict[str, Any]) -> SearchProfile:
        places = cast(list[dict[str, Any]], validated_data.pop("important_places", []))
        notification_data = cast(dict[str, Any], validated_data.pop("notification_preference", {}))
        profile = SearchProfile.objects.create(user=self.context["request"].user, **validated_data)
        ImportantPlace.objects.bulk_create(
            [ImportantPlace(search_profile=profile, **place) for place in places]
        )
        NotificationPreference.objects.create(search_profile=profile, **notification_data)
        return profile

    def update(self, instance: SearchProfile, validated_data: dict[str, Any]) -> SearchProfile:
        places = cast(list[dict[str, Any]] | None, validated_data.pop("important_places", None))
        notification_data = cast(
            dict[str, Any] | None, validated_data.pop("notification_preference", None)
        )
        for key, value in validated_data.items():
            setattr(instance, key, value)
        instance.save()
        if places is not None:
            instance.important_places.all().delete()
            ImportantPlace.objects.bulk_create(
                [ImportantPlace(search_profile=instance, **place) for place in places]
            )
        if notification_data is not None:
            NotificationPreference.objects.update_or_create(
                search_profile=instance, defaults=notification_data
            )
        return instance


class MatchQuerySerializer(serializers.Serializer):
    min_score = serializers.IntegerField(required=False, default=0, min_value=0, max_value=100)
    eligible_only = serializers.BooleanField(required=False, default=True)
    ordering = serializers.ChoiceField(
        required=False,
        default="-match_score",
        choices=("-match_score", "match_score", "-published_at", "price_uah"),
    )
    limit = serializers.IntegerField(required=False, default=100, min_value=1, max_value=500)


class NaturalLanguageSearchSerializer(serializers.Serializer):
    text = serializers.CharField(max_length=4000, trim_whitespace=True)
