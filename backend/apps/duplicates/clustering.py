from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from itertools import combinations
from typing import Any

from django.conf import settings
from django.db import transaction

from apps.duplicates.models import (
    CandidateDecision,
    ClusterJoinMethod,
    ClusterMemberRole,
    ClusterStatus,
    DuplicateCandidate,
    ListingCluster,
    ListingClusterMember,
    UserClusterState,
)
from apps.listings.models import Listing

ACCEPTED_DECISIONS = {CandidateDecision.AUTO_MERGE, CandidateDecision.CONFIRMED}


@dataclass(frozen=True)
class ClusterRunResult:
    components: int = 0
    clusters_created: int = 0
    clusters_reused: int = 0
    clusters_archived: int = 0
    members: int = 0


def _completeness_score(listing: Listing) -> int:
    values = (
        listing.description,
        listing.street,
        listing.total_area,
        listing.floor,
        listing.floors_total,
        listing.building_type,
        listing.renovation_level,
        listing.heating_type,
        listing.pets_allowed,
        listing.children_allowed,
    )
    return sum(value not in (None, "") for value in values)


def primary_quality(listing: Listing) -> tuple[Any, ...]:
    source_approved = listing.source.legal_status in {"approved", "approved_demo"}
    source_healthy = listing.source.enabled and listing.source.health_status in {"healthy", "unknown"}
    location_score = {"building": 3, "street": 2, "district": 1}.get(listing.location_accuracy, 0)
    image_count = sum(isinstance(value, str) and bool(value) for value in listing.images)
    commission = float(listing.commission_percent) if listing.commission_percent is not None else 1000.0
    return (
        int(listing.is_active),
        int(source_approved),
        int(source_healthy),
        location_score,
        image_count,
        _completeness_score(listing),
        int(listing.is_owner is True),
        -commission,
        listing.published_at.timestamp(),
        listing.last_seen_at.timestamp(),
        str(listing.id),
    )


def select_primary(listings: list[Listing]) -> Listing:
    if not listings:
        raise ValueError("Cannot select a primary listing from an empty collection")
    return max(listings, key=primary_quality)


def _pair_key(left_id: object, right_id: object) -> tuple[str, str]:
    left = str(left_id)
    right = str(right_id)
    return (left, right) if left < right else (right, left)


def _candidate_is_compatible(candidate: DuplicateCandidate | None) -> bool:
    if candidate is None or candidate.decision == CandidateDecision.SPLIT:
        return False
    if candidate.hard_conflicts:
        return False
    return (
        candidate.decision in ACCEPTED_DECISIONS
        or float(candidate.final_score) >= float(settings.DUPLICATE_REVIEW_THRESHOLD)
    )


def _component_can_merge(
    member_ids: set[str],
    listings: dict[str, Listing],
    candidates: dict[tuple[str, str], DuplicateCandidate],
) -> bool:
    pairs = list(combinations(sorted(member_ids), 2))
    compatible_pairs = 0
    for left_id, right_id in pairs:
        candidate = candidates.get(_pair_key(left_id, right_id))
        if candidate is not None and candidate.decision == CandidateDecision.SPLIT:
            return False
        compatible_pairs += int(_candidate_is_compatible(candidate))
    if len(member_ids) <= 2:
        return compatible_pairs == 1
    # Small apartment clusters must form a complete compatibility graph. This
    # prevents A≈B and B≈C from silently poisoning a cluster where A conflicts
    # with C. Larger clusters still require every member to match the primary
    # plus a strong global pair ratio.
    if len(member_ids) <= 5:
        return compatible_pairs == len(pairs)
    primary = select_primary([listings[item] for item in member_ids])
    primary_compatible = all(
        _candidate_is_compatible(candidates.get(_pair_key(primary.id, member_id)))
        for member_id in member_ids
        if member_id != str(primary.id)
    )
    required_pairs = math.ceil(len(pairs) * 0.7)
    return primary_compatible and compatible_pairs >= required_pairs


def build_guarded_components(
    listings: list[Listing],
    candidates: list[DuplicateCandidate],
) -> list[set[str]]:
    listing_map = {str(listing.id): listing for listing in listings}
    candidate_map = {
        _pair_key(candidate.left_listing_id, candidate.right_listing_id): candidate
        for candidate in candidates
    }
    parent = {listing_id: listing_id for listing_id in listing_map}
    members = {listing_id: {listing_id} for listing_id in listing_map}

    def find(item: str) -> str:
        while parent[item] != item:
            parent[item] = parent[parent[item]]
            item = parent[item]
        return item

    for candidate in sorted(
        (item for item in candidates if item.decision in ACCEPTED_DECISIONS),
        key=lambda item: (-float(item.final_score), str(item.left_listing_id), str(item.right_listing_id)),
    ):
        left_id = str(candidate.left_listing_id)
        right_id = str(candidate.right_listing_id)
        if left_id not in parent or right_id not in parent:
            continue
        left_root = find(left_id)
        right_root = find(right_id)
        if left_root == right_root:
            continue
        proposed = members[left_root] | members[right_root]
        if not _component_can_merge(proposed, listing_map, candidate_map):
            continue
        stable_root = min(left_root, right_root)
        replaced_root = right_root if stable_root == left_root else left_root
        parent[replaced_root] = stable_root
        members[stable_root] = proposed
        members.pop(replaced_root, None)

    return sorted(
        (component for component in members.values() if len(component) >= 2),
        key=lambda component: sorted(component)[0],
    )


def _candidate_to_primary(
    primary: Listing,
    listing: Listing,
    candidates: dict[tuple[str, str], DuplicateCandidate],
) -> DuplicateCandidate | None:
    return candidates.get(_pair_key(primary.id, listing.id))


def _cluster_for_component(
    component: set[str],
    existing_memberships: dict[str, ListingClusterMember],
    used_clusters: set[str],
) -> ListingCluster | None:
    overlap: dict[str, tuple[ListingCluster, int]] = {}
    for listing_id in component:
        membership = existing_memberships.get(listing_id)
        if membership is None:
            continue
        cluster_id = str(membership.cluster_id)
        cluster, count = overlap.get(cluster_id, (membership.cluster, 0))
        overlap[cluster_id] = (cluster, count + 1)
    candidates = sorted(
        (value for key, value in overlap.items() if key not in used_clusters),
        key=lambda item: (-item[1], str(item[0].id)),
    )
    return candidates[0][0] if candidates else None


@transaction.atomic
def rebuild_clusters(*, city: str | None = None, dry_run: bool = False) -> ClusterRunResult:
    listings_queryset = Listing.objects.filter(
        is_active=True,
        source__enabled=True,
        source__legal_status__in=("approved_demo", "approved"),
    ).select_related("source")
    if city:
        listings_queryset = listings_queryset.filter(city__iexact=city)
    listings = list(listings_queryset.order_by("id"))
    listing_ids = [listing.id for listing in listings]
    all_candidates = list(
        DuplicateCandidate.objects.filter(
            left_listing_id__in=listing_ids,
            right_listing_id__in=listing_ids,
        ).select_related("left_listing__source", "right_listing__source")
    )
    components = build_guarded_components(listings, all_candidates)
    if dry_run:
        return ClusterRunResult(
            components=len(components),
            members=sum(len(component) for component in components),
        )

    existing_membership_rows = list(
        ListingClusterMember.objects.select_for_update()
        .filter(listing_id__in=listing_ids)
        .select_related("cluster")
    )
    existing_memberships = {
        str(membership.listing_id): membership for membership in existing_membership_rows
    }
    affected_clusters = {membership.cluster for membership in existing_membership_rows}
    previous_primary = {str(cluster.id): cluster.primary_listing_id for cluster in affected_clusters}
    previous_states: dict[str, list[UserClusterState]] = defaultdict(list)
    for state in UserClusterState.objects.select_for_update().filter(cluster__in=affected_clusters):
        previous_states[str(state.cluster_id)].append(state)

    ListingClusterMember.objects.filter(cluster__in=affected_clusters).delete()
    archived = 0
    for cluster in affected_clusters:
        cluster.status = ClusterStatus.ARCHIVED
        cluster.member_count = 0
        cluster.source_count = 0
        cluster.primary_listing = None
        cluster.confidence_min = None
        cluster.confidence_max = None
        cluster.save(
            update_fields=(
                "status",
                "member_count",
                "source_count",
                "primary_listing",
                "confidence_min",
                "confidence_max",
                "updated_at",
            )
        )
        archived += 1

    listing_map = {str(listing.id): listing for listing in listings}
    candidate_map = {
        _pair_key(candidate.left_listing_id, candidate.right_listing_id): candidate
        for candidate in all_candidates
    }
    used_clusters: set[str] = set()
    old_to_new: dict[str, list[ListingCluster]] = defaultdict(list)
    created = 0
    reused = 0
    total_members = 0

    for component in components:
        component_listings = [listing_map[item] for item in component]
        primary = select_primary(component_listings)
        cluster = _cluster_for_component(component, existing_memberships, used_clusters)
        old_cluster_id: str | None = None
        if cluster is None:
            cluster = ListingCluster.objects.create(algorithm_version=1)
            created += 1
        else:
            old_cluster_id = str(cluster.id)
            used_clusters.add(old_cluster_id)
            reused += 1
        confidences: list[Decimal] = []
        for listing in component_listings:
            candidate = None if listing.id == primary.id else _candidate_to_primary(primary, listing, candidate_map)
            confidence = Decimal("100.00") if candidate is None else candidate.final_score
            joined_by = ClusterJoinMethod.AUTO
            reasons: list[dict[str, Any]] = []
            if candidate is not None:
                reasons = list(candidate.reasons)
                if candidate.decision == CandidateDecision.CONFIRMED:
                    joined_by = ClusterJoinMethod.MANUAL
                elif candidate.exact_score is not None and float(candidate.exact_score) >= 100:
                    joined_by = ClusterJoinMethod.EXACT
            ListingClusterMember.objects.create(
                cluster=cluster,
                listing=listing,
                role=(ClusterMemberRole.PRIMARY if listing.id == primary.id else ClusterMemberRole.DUPLICATE),
                confidence=confidence,
                joined_by=joined_by,
                reasons=reasons,
            )
            confidences.append(confidence)
        cluster.status = ClusterStatus.ACTIVE
        cluster.primary_listing = primary
        cluster.member_count = len(component_listings)
        cluster.source_count = len({listing.source_id for listing in component_listings})
        cluster.confidence_min = min(confidences)
        cluster.confidence_max = max(confidences)
        cluster.algorithm_version = 1
        cluster.save(
            update_fields=(
                "status",
                "primary_listing",
                "member_count",
                "source_count",
                "confidence_min",
                "confidence_max",
                "algorithm_version",
                "updated_at",
            )
        )
        total_members += len(component_listings)
        source_old_ids = {
            str(existing_memberships[item].cluster_id)
            for item in component
            if item in existing_memberships
        }
        for source_old_id in source_old_ids:
            old_to_new[source_old_id].append(cluster)
        if old_cluster_id is not None and old_cluster_id not in source_old_ids:
            old_to_new[old_cluster_id].append(cluster)

    for old_cluster_id, states in previous_states.items():
        target_clusters = list({cluster.id: cluster for cluster in old_to_new.get(old_cluster_id, [])}.values())
        for state in states:
            for target in target_clusters:
                if target.id == state.cluster_id:
                    state.cluster = target
                    state.save(update_fields=("cluster", "updated_at"))
                    continue
                preserve_compared = previous_primary.get(old_cluster_id) == target.primary_listing_id
                UserClusterState.objects.update_or_create(
                    user=state.user,
                    cluster=target,
                    defaults={
                        "is_favorite": state.is_favorite,
                        "is_hidden": state.is_hidden,
                        "is_compared": state.is_compared and preserve_compared,
                        "note": state.note,
                    },
                )

    return ClusterRunResult(
        components=len(components),
        clusters_created=created,
        clusters_reused=reused,
        clusters_archived=archived,
        members=total_members,
    )
