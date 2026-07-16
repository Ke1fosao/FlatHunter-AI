from __future__ import annotations

from typing import Any, cast

from rest_framework import serializers

from apps.accounts.models import User
from apps.duplicates.models import DuplicateCandidate, ListingCluster, UserClusterState
from apps.duplicates.presentation import cluster_members
from apps.duplicates.services import cluster_state_payload, get_user_cluster_state
from apps.listings.serializers import ListingSerializer
from apps.matching.engine import evaluate_match
from apps.searches.models import SearchProfile


class UserClusterStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserClusterState
        fields = ("is_favorite", "is_hidden", "is_compared", "note", "updated_at")
        read_only_fields = fields


class ClusterStateMutationSerializer(serializers.Serializer):
    is_favorite = serializers.BooleanField(required=False)
    is_hidden = serializers.BooleanField(required=False)
    is_compared = serializers.BooleanField(required=False)
    note = serializers.CharField(required=False, allow_blank=True, max_length=500)

    def validate(self, attrs: dict[str, Any]) -> dict[str, Any]:
        if not attrs:
            raise serializers.ValidationError("Передайте хоча б одне поле стану.")
        return attrs


class CandidateReviewSerializer(serializers.Serializer):
    note = serializers.CharField(required=False, allow_blank=True, max_length=1000)


class DuplicateCandidateSerializer(serializers.ModelSerializer):
    left_title = serializers.CharField(source="left_listing.title", read_only=True)
    right_title = serializers.CharField(source="right_listing.title", read_only=True)

    class Meta:
        model = DuplicateCandidate
        fields = (
            "id",
            "left_listing",
            "right_listing",
            "left_title",
            "right_title",
            "exact_score",
            "address_score",
            "geo_score",
            "attributes_score",
            "text_score",
            "image_score",
            "price_score",
            "final_score",
            "decision",
            "reasons",
            "hard_conflicts",
            "algorithm_version",
            "evaluated_at",
            "reviewed_at",
            "review_note",
        )
        read_only_fields = fields


class ListingClusterDetailSerializer(serializers.ModelSerializer):
    primary = serializers.SerializerMethodField()
    members = serializers.SerializerMethodField()
    user_state = serializers.SerializerMethodField()
    price_min_uah = serializers.SerializerMethodField()
    price_max_uah = serializers.SerializerMethodField()
    match = serializers.SerializerMethodField()

    class Meta:
        model = ListingCluster
        fields = (
            "id",
            "status",
            "primary",
            "member_count",
            "source_count",
            "confidence_min",
            "confidence_max",
            "price_min_uah",
            "price_max_uah",
            "members",
            "user_state",
            "match",
            "algorithm_version",
            "created_at",
            "updated_at",
        )
        read_only_fields = fields

    def get_primary(self, cluster: ListingCluster) -> dict[str, Any] | None:
        if cluster.primary_listing is None:
            return None
        return ListingSerializer(cluster.primary_listing, context=self.context).data

    def get_members(self, cluster: ListingCluster) -> list[dict[str, Any]]:
        result: list[dict[str, Any]] = []
        for member in cluster_members(cluster):
            if not member.listing.is_active:
                continue
            concise_reasons = [
                str(item.get("message", ""))
                for item in member.reasons
                if isinstance(item, dict) and item.get("message")
            ][:3]
            result.append(
                {
                    "role": member.role,
                    "confidence": member.confidence,
                    "joined_by": member.joined_by,
                    "reasons": concise_reasons,
                    "listing": ListingSerializer(member.listing, context=self.context).data,
                }
            )
        return result

    def get_user_state(self, cluster: ListingCluster) -> dict[str, Any]:
        request = self.context.get("request")
        if request is None or not request.user.is_authenticated:
            return cluster_state_payload(None)
        return cluster_state_payload(get_user_cluster_state(cluster, cast(User, request.user)))

    def _prices(self, cluster: ListingCluster) -> list[int]:
        return [
            member.listing.price_uah
            for member in cluster_members(cluster)
            if member.listing.is_active
        ]

    def get_price_min_uah(self, cluster: ListingCluster) -> int | None:
        prices = self._prices(cluster)
        return min(prices) if prices else None

    def get_price_max_uah(self, cluster: ListingCluster) -> int | None:
        prices = self._prices(cluster)
        return max(prices) if prices else None

    def get_match(self, cluster: ListingCluster) -> dict[str, Any] | None:
        profile = self.context.get("profile")
        if not isinstance(profile, SearchProfile) or cluster.primary_listing is None:
            return None
        return evaluate_match(profile, cluster.primary_listing).to_dict()
