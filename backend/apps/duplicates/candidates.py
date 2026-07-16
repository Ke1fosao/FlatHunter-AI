from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import User
from apps.duplicates.fingerprints import get_fresh_fingerprint
from apps.duplicates.models import (
    CandidateDecision,
    DecisionAction,
    DuplicateCandidate,
    DuplicateDecision,
    ListingFingerprint,
)
from apps.duplicates.normalization import hamming_distance64
from apps.duplicates.scoring import DuplicateEvaluation, evaluate_duplicate
from apps.listings.models import Listing


@dataclass(frozen=True)
class CandidateRunResult:
    inspected: int = 0
    created: int = 0
    updated: int = 0
    auto_merge: int = 0
    needs_review: int = 0
    rejected: int = 0
    blocked: int = 0
    failed: int = 0


def canonical_pair(left: Listing, right: Listing) -> tuple[Listing, Listing]:
    if left.pk == right.pk:
        raise ValueError("A listing cannot be compared with itself")
    return (left, right) if str(left.pk) < str(right.pk) else (right, left)


def _exact_image_hashes(fingerprint: ListingFingerprint) -> set[str]:
    return {
        str(item["exact"])
        for item in fingerprint.image_hashes
        if isinstance(item, dict) and item.get("exact")
    }


def _shares_candidate_block(left: ListingFingerprint, right: ListingFingerprint) -> bool:
    if left.normalized_url and left.normalized_url == right.normalized_url:
        return True
    if set(left.contact_hashes) & set(right.contact_hashes):
        return True
    if left.address_key and left.address_key == right.address_key:
        return True
    if left.geo_block_key and left.geo_block_key == right.geo_block_key:
        return True
    if (
        left.attribute_key
        and left.attribute_key == right.attribute_key
        and abs(left.price_bucket - right.price_bucket) <= 3
    ):
        return True
    if _exact_image_hashes(left) & _exact_image_hashes(right):
        return True
    return bool(
        left.text_block_key
        and left.text_block_key == right.text_block_key
        and hamming_distance64(left.text_simhash, right.text_simhash)
        <= settings.DUPLICATE_SIMHASH_BLOCK_DISTANCE
    )


def candidate_pairs_for_listing(
    listing: Listing,
    *,
    limit: int | None = None,
) -> list[tuple[Listing, Listing]]:
    fingerprint = get_fresh_fingerprint(listing)
    block_limit = min(limit or settings.DUPLICATE_BLOCK_LIMIT, settings.DUPLICATE_BLOCK_LIMIT)
    query = (
        ListingFingerprint.objects.filter(
            normalized_city=fingerprint.normalized_city,
            listing__is_active=True,
            listing__source__enabled=True,
            listing__source__legal_status__in=("approved_demo", "approved"),
        )
        .exclude(listing=listing)
        .select_related("listing", "listing__source")
        .order_by("listing_id")[:block_limit]
    )
    pairs: list[tuple[Listing, Listing]] = []
    for other_fingerprint in query:
        if _shares_candidate_block(fingerprint, other_fingerprint):
            pairs.append(canonical_pair(listing, other_fingerprint.listing))
    return pairs


def _preserved_manual_decision(candidate: DuplicateCandidate | None) -> str | None:
    if candidate is None:
        return None
    if candidate.decision in {CandidateDecision.CONFIRMED, CandidateDecision.SPLIT}:
        return candidate.decision
    return None


@transaction.atomic
def persist_candidate_evaluation(
    left: Listing,
    right: Listing,
    evaluation: DuplicateEvaluation,
    *,
    dry_run: bool = False,
) -> tuple[DuplicateCandidate | None, bool, bool]:
    left, right = canonical_pair(left, right)
    existing = (
        DuplicateCandidate.objects.select_for_update()
        .filter(left_listing=left, right_listing=right)
        .first()
    )
    if dry_run:
        return existing, existing is None, existing is not None
    defaults = evaluation.candidate_defaults()
    preserved = _preserved_manual_decision(existing)
    if preserved is not None:
        defaults["decision"] = preserved
    candidate, created = DuplicateCandidate.objects.update_or_create(
        left_listing=left,
        right_listing=right,
        defaults=defaults,
    )
    return candidate, created, not created


def evaluate_pair(left: Listing, right: Listing) -> DuplicateEvaluation:
    left, right = canonical_pair(left, right)
    return evaluate_duplicate(
        left,
        right,
        get_fresh_fingerprint(left),
        get_fresh_fingerprint(right),
    )


def evaluate_listing_candidates(
    listing: Listing,
    *,
    limit: int | None = None,
    dry_run: bool = False,
) -> CandidateRunResult:
    counters: dict[str, int] = {
        "inspected": 0,
        "created": 0,
        "updated": 0,
        "auto_merge": 0,
        "needs_review": 0,
        "rejected": 0,
        "blocked": 0,
        "failed": 0,
    }
    for left, right in candidate_pairs_for_listing(listing, limit=limit):
        counters["inspected"] += 1
        try:
            evaluation = evaluate_pair(left, right)
            candidate, created, updated = persist_candidate_evaluation(
                left,
                right,
                evaluation,
                dry_run=dry_run,
            )
            counters["created"] += int(created)
            counters["updated"] += int(updated)
            decision = candidate.decision if candidate is not None else evaluation.decision
            if decision == CandidateDecision.SPLIT:
                counters["blocked"] += 1
            elif decision == CandidateDecision.AUTO_MERGE:
                counters["auto_merge"] += 1
            elif decision == CandidateDecision.NEEDS_REVIEW:
                counters["needs_review"] += 1
            elif decision == CandidateDecision.REJECTED:
                counters["rejected"] += 1
        except Exception:
            counters["failed"] += 1
    return CandidateRunResult(**counters)


def detect_listing_duplicates(
    *,
    listing_id: UUID | str | None = None,
    city: str | None = None,
    limit: int | None = None,
    dry_run: bool = False,
) -> CandidateRunResult:
    queryset = Listing.objects.filter(
        is_active=True,
        source__enabled=True,
        source__legal_status__in=("approved_demo", "approved"),
    ).select_related("source")
    if listing_id is not None:
        queryset = queryset.filter(pk=listing_id)
    if city:
        queryset = queryset.filter(city__iexact=city)
    if limit is not None:
        queryset = queryset[: max(1, min(limit, 5000))]

    aggregate = CandidateRunResult()
    for listing in queryset.iterator(chunk_size=200):
        result = evaluate_listing_candidates(listing, dry_run=dry_run)
        aggregate = CandidateRunResult(
            inspected=aggregate.inspected + result.inspected,
            created=aggregate.created + result.created,
            updated=aggregate.updated + result.updated,
            auto_merge=aggregate.auto_merge + result.auto_merge,
            needs_review=aggregate.needs_review + result.needs_review,
            rejected=aggregate.rejected + result.rejected,
            blocked=aggregate.blocked + result.blocked,
            failed=aggregate.failed + result.failed,
        )
    return aggregate


@transaction.atomic
def _record_manual_decision(
    candidate: DuplicateCandidate,
    *,
    actor: User | None,
    note: str,
    action: str,
    candidate_decision: str,
) -> DuplicateCandidate:
    candidate = DuplicateCandidate.objects.select_for_update().get(pk=candidate.pk)
    candidate.decision = candidate_decision
    candidate.reviewed_at = timezone.now()
    candidate.reviewed_by = actor
    candidate.review_note = note[:1000]
    candidate.save(
        update_fields=("decision", "reviewed_at", "reviewed_by", "review_note", "evaluated_at")
    )
    DuplicateDecision.objects.create(
        candidate=candidate,
        left_listing=candidate.left_listing,
        right_listing=candidate.right_listing,
        action=action,
        actor=actor,
        note=note[:1000],
    )
    return candidate


def confirm_candidate(
    candidate: DuplicateCandidate,
    *,
    actor: User | None,
    note: str = "",
) -> DuplicateCandidate:
    return _record_manual_decision(
        candidate,
        actor=actor,
        note=note,
        action=DecisionAction.CONFIRM,
        candidate_decision=CandidateDecision.CONFIRMED,
    )


def split_candidate(
    candidate: DuplicateCandidate,
    *,
    actor: User | None,
    note: str = "",
) -> DuplicateCandidate:
    return _record_manual_decision(
        candidate,
        actor=actor,
        note=note,
        action=DecisionAction.BLOCK_PAIR,
        candidate_decision=CandidateDecision.SPLIT,
    )


def restore_candidate_auto(
    candidate: DuplicateCandidate,
    *,
    actor: User | None,
    note: str = "",
) -> DuplicateCandidate:
    evaluation = evaluate_pair(candidate.left_listing, candidate.right_listing)
    candidate = _record_manual_decision(
        candidate,
        actor=actor,
        note=note,
        action=DecisionAction.RESTORE_AUTO,
        candidate_decision=evaluation.decision,
    )
    defaults = evaluation.candidate_defaults()
    for field, value in defaults.items():
        if field != "decision":
            setattr(candidate, field, value)
    candidate.save(
        update_fields=(
            "exact_score",
            "address_score",
            "geo_score",
            "attributes_score",
            "text_score",
            "image_score",
            "price_score",
            "final_score",
            "reasons",
            "hard_conflicts",
            "algorithm_version",
            "evaluated_at",
        )
    )
    return candidate
