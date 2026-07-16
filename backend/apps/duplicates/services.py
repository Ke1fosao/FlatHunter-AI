from __future__ import annotations

from dataclasses import dataclass
from typing import Any
from uuid import UUID

from celery import current_app
from django.conf import settings
from django.db import transaction

from apps.accounts.models import User
from apps.duplicates.candidates import CandidateRunResult, evaluate_listing_candidates
from apps.duplicates.clustering import ClusterRunResult, rebuild_clusters
from apps.duplicates.fingerprints import FingerprintBuildResult, build_listing_fingerprint
from apps.duplicates.models import ListingCluster, UserClusterState
from apps.listings.models import Listing, UserListingState


class ComparisonLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class RefreshResult:
    fingerprint: FingerprintBuildResult
    candidates: CandidateRunResult
    clusters: ClusterRunResult


def refresh_listing_duplicates(listing_id: UUID | str) -> RefreshResult:
    listing = Listing.objects.select_related("source").get(pk=listing_id)
    fingerprint = build_listing_fingerprint(listing)
    candidates = evaluate_listing_candidates(listing)
    clusters = rebuild_clusters(city=listing.city)
    return RefreshResult(fingerprint=fingerprint, candidates=candidates, clusters=clusters)


def schedule_listing_duplicate_refresh(listing_id: UUID | str) -> bool:
    if not settings.DUPLICATE_AUTO_QUEUE_ENABLED:
        return False
    current_app.send_task(
        "apps.duplicates.tasks.refresh_listing_duplicates_task",
        args=[str(listing_id)],
        queue=settings.DUPLICATE_TASK_QUEUE,
    )
    return True


def cluster_state_payload(state: UserClusterState | None) -> dict[str, Any]:
    if state is None:
        return {
            "is_favorite": False,
            "is_hidden": False,
            "is_compared": False,
            "note": "",
            "updated_at": None,
        }
    return {
        "is_favorite": state.is_favorite,
        "is_hidden": state.is_hidden,
        "is_compared": state.is_compared,
        "note": state.note,
        "updated_at": state.updated_at,
    }


def get_user_cluster_state(cluster: ListingCluster, user: User) -> UserClusterState | None:
    prefetched = getattr(cluster, "current_user_cluster_states", None)
    if isinstance(prefetched, list):
        return prefetched[0] if prefetched else None
    return UserClusterState.objects.filter(cluster=cluster, user=user).first()


@transaction.atomic
def update_cluster_state(
    *,
    cluster: ListingCluster,
    user: User,
    values: dict[str, Any],
) -> UserClusterState:
    cluster = ListingCluster.objects.select_for_update().get(
        pk=cluster.pk,
        status="active",
    )
    state = UserClusterState.objects.select_for_update().filter(cluster=cluster, user=user).first()
    state_is_new = state is None
    if state is None:
        state = UserClusterState(user=user, cluster=cluster)
        if cluster.primary_listing_id is not None:
            primary_state = UserListingState.objects.filter(
                user=user,
                listing_id=cluster.primary_listing_id,
            ).first()
            if primary_state is not None:
                state.is_favorite = primary_state.is_favorite
                state.is_hidden = primary_state.is_hidden
                state.is_compared = primary_state.is_compared
                state.note = primary_state.note

    if values.get("is_compared") is True and not state.is_compared:
        cluster_compared = (
            UserClusterState.objects.select_for_update()
            .filter(user=user, is_compared=True)
            .exclude(cluster=cluster)
            .count()
        )
        standalone_compared = (
            UserListingState.objects.select_for_update()
            .filter(
                user=user,
                is_compared=True,
                listing__cluster_membership__isnull=True,
            )
            .count()
        )
        if cluster_compared + standalone_compared >= 4:
            raise ComparisonLimitError("Можна порівнювати до 4 квартир.")

    mutable_fields = ("is_favorite", "is_hidden", "is_compared", "note")
    changed_fields: list[str] = []
    for field in mutable_fields:
        if field in values:
            setattr(state, field, values[field])
            changed_fields.append(field)
    if state_is_new:
        state.save()
    elif changed_fields:
        state.save(update_fields=(*changed_fields, "updated_at"))

    member_ids = list(cluster.members.values_list("listing_id", flat=True))
    member_states = UserListingState.objects.select_for_update().filter(
        user=user,
        listing_id__in=member_ids,
    )
    for field in ("is_favorite", "is_hidden", "is_compared"):
        if field not in values:
            continue
        member_states.update(**{field: False})
    if cluster.primary_listing_id is not None:
        primary_state, _ = UserListingState.objects.get_or_create(
            user=user,
            listing_id=cluster.primary_listing_id,
        )
        primary_changed: list[str] = []
        for field in ("is_favorite", "is_hidden", "is_compared", "note"):
            if field in values:
                setattr(primary_state, field, values[field])
                primary_changed.append(field)
        if primary_changed:
            primary_state.save(update_fields=(*primary_changed, "updated_at"))
    return state
