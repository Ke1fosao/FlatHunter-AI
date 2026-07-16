from django.contrib import admin
from django.http import HttpRequest

from apps.duplicates.models import (
    DuplicateCandidate,
    DuplicateDecision,
    ListingCluster,
    ListingClusterMember,
    ListingFingerprint,
    UserClusterState,
)


@admin.register(ListingFingerprint)
class ListingFingerprintAdmin(admin.ModelAdmin):
    list_display = (
        "listing",
        "version",
        "normalized_city",
        "address_key",
        "generated_at",
        "last_error",
    )
    list_filter = ("version", "normalized_city", "image_hash_version")
    search_fields = (
        "listing__title",
        "listing__external_id",
        "address_key",
        "attribute_key",
        "normalized_url",
    )
    readonly_fields = ("generated_at",)


@admin.register(DuplicateCandidate)
class DuplicateCandidateAdmin(admin.ModelAdmin):
    list_display = (
        "left_listing",
        "right_listing",
        "final_score",
        "decision",
        "algorithm_version",
        "evaluated_at",
    )
    list_filter = ("decision", "algorithm_version", "evaluated_at")
    search_fields = (
        "left_listing__title",
        "right_listing__title",
        "left_listing__external_id",
        "right_listing__external_id",
    )
    readonly_fields = ("evaluated_at",)
    autocomplete_fields = ("left_listing", "right_listing", "reviewed_by")


class ListingClusterMemberInline(admin.TabularInline):
    model = ListingClusterMember
    extra = 0
    autocomplete_fields = ("listing",)
    readonly_fields = ("joined_at",)


@admin.register(ListingCluster)
class ListingClusterAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "primary_listing",
        "status",
        "member_count",
        "source_count",
        "confidence_min",
        "confidence_max",
        "updated_at",
    )
    list_filter = ("status", "algorithm_version")
    search_fields = ("id", "primary_listing__title", "primary_listing__external_id")
    autocomplete_fields = ("primary_listing",)
    readonly_fields = ("created_at", "updated_at")
    inlines = (ListingClusterMemberInline,)


@admin.register(ListingClusterMember)
class ListingClusterMemberAdmin(admin.ModelAdmin):
    list_display = ("cluster", "listing", "role", "confidence", "joined_by", "joined_at")
    list_filter = ("role", "joined_by")
    search_fields = ("cluster__id", "listing__title", "listing__external_id")
    autocomplete_fields = ("cluster", "listing")
    readonly_fields = ("joined_at",)


@admin.register(DuplicateDecision)
class DuplicateDecisionAdmin(admin.ModelAdmin):
    list_display = ("action", "left_listing", "right_listing", "actor", "created_at")
    list_filter = ("action", "created_at")
    search_fields = ("left_listing__title", "right_listing__title", "note")
    readonly_fields = (
        "id",
        "candidate",
        "left_listing",
        "right_listing",
        "action",
        "actor",
        "note",
        "created_at",
    )

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def has_change_permission(self, request: HttpRequest, obj: object | None = None) -> bool:
        return False


@admin.register(UserClusterState)
class UserClusterStateAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "cluster",
        "is_favorite",
        "is_hidden",
        "is_compared",
        "updated_at",
    )
    list_filter = ("is_favorite", "is_hidden", "is_compared")
    search_fields = ("user__username", "cluster__primary_listing__title", "note")
    autocomplete_fields = ("user", "cluster")
    readonly_fields = ("created_at", "updated_at")
