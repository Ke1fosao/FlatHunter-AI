from __future__ import annotations

from typing import Any

from django.db.models import Prefetch, QuerySet

from apps.accounts.models import User
from apps.duplicates.models import (
    ClusterMemberRole,
    ClusterStatus,
    ListingCluster,
    ListingClusterMember,
    UserClusterState,
)
from apps.duplicates.services import cluster_state_payload, get_user_cluster_state
from apps.listings.models import Listing, UserListingState


def presentation_queryset(queryset: QuerySet[Listing], user: User) -> QuerySet[Listing]:
    listing_states = UserListingState.objects.filter(user=user)
    cluster_states = UserClusterState.objects.filter(user=user)
    cluster_members = ListingClusterMember.objects.select_related(
        "listing",
        "listing__source",
    ).order_by("role", "-confidence", "listing__published_at")
    return queryset.select_related(
        "source",
        "cluster_membership__cluster",
        "cluster_membership__cluster__primary_listing",
    ).prefetch_related(
        Prefetch("user_states", queryset=listing_states, to_attr="current_user_states"),
        Prefetch(
            "cluster_membership__cluster__user_states",
            queryset=cluster_states,
            to_attr="current_user_cluster_states",
        ),
        Prefetch(
            "cluster_membership__cluster__members",
            queryset=cluster_members,
            to_attr="current_members",
        ),
    )


def collapse_clustered_queryset(queryset: QuerySet[Listing]) -> QuerySet[Listing]:
    return queryset.exclude(
        cluster_membership__cluster__status=ClusterStatus.ACTIVE,
        cluster_membership__role=ClusterMemberRole.DUPLICATE,
    )


def cluster_membership_for(listing: Listing) -> ListingClusterMember | None:
    try:
        membership = listing.cluster_membership
    except ListingClusterMember.DoesNotExist:
        return None
    return membership if membership.cluster.status == ClusterStatus.ACTIVE else None


def cluster_for_listing(listing: Listing) -> ListingCluster | None:
    membership = cluster_membership_for(listing)
    return membership.cluster if membership is not None else None


def cluster_members(cluster: ListingCluster) -> list[ListingClusterMember]:
    prefetched = getattr(cluster, "current_members", None)
    if isinstance(prefetched, list):
        return prefetched
    return list(
        cluster.members.select_related("listing", "listing__source").order_by(
            "role",
            "-confidence",
            "-listing__published_at",
        )
    )


def cluster_metadata(listing: Listing) -> dict[str, Any]:
    membership = cluster_membership_for(listing)
    if membership is None:
        return {
            "cluster_id": None,
            "source_count": 1,
            "member_count": 1,
            "is_cluster_primary": True,
            "price_min_uah": listing.price_uah,
            "price_max_uah": listing.price_uah,
        }
    cluster = membership.cluster
    members = cluster_members(cluster)
    active_members = [member for member in members if member.listing.is_active]
    prices = [member.listing.price_uah for member in active_members] or [listing.price_uah]
    return {
        "cluster_id": str(cluster.id),
        "source_count": cluster.source_count,
        "member_count": cluster.member_count,
        "is_cluster_primary": membership.role == ClusterMemberRole.PRIMARY,
        "price_min_uah": min(prices),
        "price_max_uah": max(prices),
    }


def projected_user_state(listing: Listing, user: User) -> dict[str, Any]:
    cluster = cluster_for_listing(listing)
    if cluster is not None:
        return cluster_state_payload(get_user_cluster_state(cluster, user))
    states = getattr(listing, "current_user_states", None)
    if isinstance(states, list):
        state = states[0] if states else None
    else:
        state = UserListingState.objects.filter(user=user, listing=listing).first()
    if state is None:
        return cluster_state_payload(None)
    return {
        "is_favorite": state.is_favorite,
        "is_hidden": state.is_hidden,
        "is_compared": state.is_compared,
        "note": state.note,
        "updated_at": state.updated_at,
    }


def _state_listing_ids(user: User, field: str) -> tuple[QuerySet[Any], QuerySet[Any]]:
    standalone = UserListingState.objects.filter(
        user=user,
        listing__cluster_membership__isnull=True,
        **{field: True},
    ).values("listing_id")
    clustered = ListingClusterMember.objects.filter(
        role=ClusterMemberRole.PRIMARY,
        cluster__status=ClusterStatus.ACTIVE,
        cluster__user_states__user=user,
        **{f"cluster__user_states__{field}": True},
    ).values("listing_id")
    return standalone, clustered


def filter_listing_state(
    queryset: QuerySet[Listing],
    *,
    user: User,
    field: str,
    value: bool,
) -> QuerySet[Listing]:
    standalone, clustered = _state_listing_ids(user, field)
    matching = queryset.filter(id__in=standalone) | queryset.filter(id__in=clustered)
    if value:
        return matching.distinct()
    ids = matching.values("id")
    return queryset.exclude(id__in=ids)


def exclude_hidden(queryset: QuerySet[Listing], user: User) -> QuerySet[Listing]:
    return filter_listing_state(queryset, user=user, field="is_hidden", value=False)


def cluster_aware_listing_queryset(
    queryset: QuerySet[Listing],
    *,
    user: User,
    include_duplicates: bool = False,
    include_hidden: bool = False,
) -> QuerySet[Listing]:
    if not include_duplicates:
        queryset = collapse_clustered_queryset(queryset)
    if not include_hidden:
        queryset = exclude_hidden(queryset, user)
    return presentation_queryset(queryset.distinct(), user)
