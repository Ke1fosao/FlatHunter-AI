from rest_framework import serializers

from apps.analysis.models import (
    ListingMarketAssessment,
    ListingPriceHistory,
    ListingRiskAssessment,
)


class ListingPriceHistorySerializer(serializers.ModelSerializer):
    class Meta:
        model = ListingPriceHistory
        fields = (
            "id",
            "previous_price_uah",
            "new_price_uah",
            "change_amount_uah",
            "change_percent",
            "direction",
            "changed_at",
            "detected_at",
        )
        read_only_fields = fields


class ListingMarketAssessmentSerializer(serializers.ModelSerializer):
    is_stale = serializers.SerializerMethodField()

    class Meta:
        model = ListingMarketAssessment
        fields = (
            "id",
            "status",
            "provider",
            "algorithm_version",
            "median_price_uah",
            "q1_price_uah",
            "q3_price_uah",
            "median_price_per_sqm",
            "target_price_per_sqm",
            "deviation_percent",
            "comparable_count",
            "confidence_score",
            "confidence_label",
            "selection_summary",
            "explanation",
            "calculated_at",
            "valid_until",
            "is_stale",
        )
        read_only_fields = fields

    def get_is_stale(self, instance: ListingMarketAssessment) -> bool:
        from django.utils import timezone

        return bool(instance.valid_until and instance.valid_until <= timezone.now())


class ListingRiskAssessmentSerializer(serializers.ModelSerializer):
    is_stale = serializers.SerializerMethodField()

    class Meta:
        model = ListingRiskAssessment
        fields = (
            "id",
            "status",
            "score",
            "level",
            "signals",
            "protective_signals",
            "summary",
            "safety_advice",
            "algorithm_version",
            "calculated_at",
            "valid_until",
            "is_stale",
        )
        read_only_fields = fields

    def get_is_stale(self, instance: ListingRiskAssessment) -> bool:
        from django.utils import timezone

        return bool(instance.valid_until and instance.valid_until <= timezone.now())


class ListingAnalysisRefreshSerializer(serializers.Serializer):
    force = serializers.BooleanField(required=False, default=False)
