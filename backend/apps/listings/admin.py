from django.contrib import admin

from apps.listings.models import Listing, ListingSource, RawListing


@admin.register(ListingSource)
class ListingSourceAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "display_name",
        "enabled",
        "access_mode",
        "legal_status",
        "health_status",
    )
    list_filter = ("enabled", "access_mode", "legal_status", "health_status")
    search_fields = ("code", "display_name")


@admin.register(RawListing)
class RawListingAdmin(admin.ModelAdmin):
    list_display = (
        "external_id",
        "source",
        "fetched_at",
        "normalized_at",
        "expires_at",
    )
    list_filter = ("source", "normalized_at")
    search_fields = ("external_id", "payload_hash")
    readonly_fields = ("id", "payload_hash", "fetched_at", "normalized_at")


@admin.register(Listing)
class ListingAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "city",
        "district",
        "rooms",
        "price_uah",
        "source",
        "is_active",
    )
    list_filter = ("source", "city", "rooms", "is_active", "building_type")
    search_fields = (
        "title",
        "description",
        "external_id",
        "city",
        "district",
        "street",
    )
    readonly_fields = ("id", "first_seen_at", "last_seen_at")
