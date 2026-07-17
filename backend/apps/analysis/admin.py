from django.contrib import admin

from apps.analysis.models import (
    ListingMarketAssessment,
    ListingPriceHistory,
    ListingRiskAssessment,
    ListingSnapshot,
)


@admin.register(ListingSnapshot)
class ListingSnapshotAdmin(admin.ModelAdmin):
    list_display = ("listing", "price_uah", "city", "captured_at")
    list_filter = ("city", "is_active", "currency")
    search_fields = ("listing__title", "listing__external_id", "content_hash")
    readonly_fields = ("captured_at", "content_hash", "title_hash", "description_hash")


@admin.register(ListingPriceHistory)
class ListingPriceHistoryAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "previous_price_uah",
        "new_price_uah",
        "direction",
        "changed_at",
    )
    list_filter = ("direction",)
    search_fields = ("listing__title", "listing__external_id")
    readonly_fields = ("detected_at",)


@admin.register(ListingMarketAssessment)
class ListingMarketAssessmentAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "status",
        "median_price_uah",
        "comparable_count",
        "confidence_label",
        "calculated_at",
    )
    list_filter = ("status", "confidence_label", "provider")
    search_fields = ("listing__title", "listing__external_id", "input_hash")
    readonly_fields = ("calculated_at", "input_hash")


@admin.register(ListingRiskAssessment)
class ListingRiskAssessmentAdmin(admin.ModelAdmin):
    list_display = ("listing", "status", "score", "level", "calculated_at")
    list_filter = ("status", "level")
    search_fields = ("listing__title", "listing__external_id", "input_hash")
    readonly_fields = ("calculated_at", "input_hash")
