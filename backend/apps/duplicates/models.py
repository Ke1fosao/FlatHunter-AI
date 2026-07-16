from __future__ import annotations

import uuid
from typing import Any

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import F, Q

from apps.listings.models import Listing


class CandidateDecision(models.TextChoices):
    AUTO_MERGE = "auto_merge", "Auto merge"
    NEEDS_REVIEW = "needs_review", "Needs review"
    REJECTED = "rejected", "Rejected"
    CONFIRMED = "confirmed", "Confirmed"
    SPLIT = "split", "Split / blocked"


class ClusterStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    SPLIT = "split", "Split"
    ARCHIVED = "archived", "Archived"


class ClusterMemberRole(models.TextChoices):
    PRIMARY = "primary", "Primary"
    DUPLICATE = "duplicate", "Duplicate"


class ClusterJoinMethod(models.TextChoices):
    AUTO = "auto", "Automatic"
    MANUAL = "manual", "Manual"
    EXACT = "exact", "Exact rule"


class DecisionAction(models.TextChoices):
    CONFIRM = "confirm", "Confirm"
    SPLIT = "split", "Split"
    BLOCK_PAIR = "block_pair", "Block pair"
    RESTORE_AUTO = "restore_auto", "Restore automatic policy"


class ListingFingerprint(models.Model):
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="duplicate_fingerprint",
        primary_key=True,
    )
    version = models.PositiveSmallIntegerField(default=1)
    normalized_city = models.CharField(max_length=120, db_index=True)
    normalized_district = models.CharField(max_length=120, blank=True)
    normalized_street = models.CharField(max_length=160, blank=True)
    normalized_title = models.CharField(max_length=500, blank=True)
    normalized_description = models.TextField(blank=True)
    normalized_url = models.CharField(max_length=500, blank=True, db_index=True)
    address_key = models.CharField(max_length=320, blank=True, db_index=True)
    geo_block_key = models.CharField(max_length=96, blank=True, db_index=True)
    attribute_key = models.CharField(max_length=320, blank=True, db_index=True)
    price_bucket = models.PositiveIntegerField(default=0, db_index=True)
    text_simhash = models.CharField(max_length=16, blank=True)
    text_block_key = models.CharField(max_length=64, blank=True, db_index=True)
    contact_hashes = models.JSONField(default=list, blank=True)
    image_hashes = models.JSONField(default=list, blank=True)
    image_hash_version = models.PositiveSmallIntegerField(default=1)
    generated_at = models.DateTimeField(auto_now=True)
    source_updated_at = models.DateTimeField()
    last_error = models.CharField(max_length=500, blank=True)

    class Meta:
        indexes = [
            models.Index(
                fields=("normalized_city", "address_key"),
                name="dup_fp_city_address_idx",
            ),
            models.Index(
                fields=("normalized_city", "attribute_key", "price_bucket"),
                name="dup_fp_attr_price_idx",
            ),
            models.Index(
                fields=("normalized_city", "geo_block_key"),
                name="dup_fp_city_geo_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"Fingerprint {self.listing_id} v{self.version}"


class DuplicateCandidate(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    left_listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="duplicate_candidates_left",
    )
    right_listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="duplicate_candidates_right",
    )
    exact_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    address_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    geo_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    attributes_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    text_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    image_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    price_score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    final_score = models.DecimalField(max_digits=5, decimal_places=2, default=0, db_index=True)
    decision = models.CharField(
        max_length=24,
        choices=CandidateDecision.choices,
        default=CandidateDecision.REJECTED,
        db_index=True,
    )
    reasons = models.JSONField(default=list, blank=True)
    hard_conflicts = models.JSONField(default=list, blank=True)
    algorithm_version = models.PositiveSmallIntegerField(default=1)
    evaluated_at = models.DateTimeField(auto_now=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_candidate_reviews",
    )
    review_note = models.CharField(max_length=1000, blank=True)

    class Meta:
        ordering = ("-final_score", "left_listing_id", "right_listing_id")
        constraints = [
            models.UniqueConstraint(
                fields=("left_listing", "right_listing"),
                name="dup_candidate_pair_unique",
            ),
            models.CheckConstraint(
                condition=~Q(left_listing=F("right_listing")),
                name="dup_candidate_distinct",
            ),
        ]
        indexes = [
            models.Index(fields=("decision", "-final_score"), name="dup_candidate_decision_idx"),
            models.Index(fields=("left_listing", "decision"), name="dup_candidate_left_idx"),
            models.Index(fields=("right_listing", "decision"), name="dup_candidate_right_idx"),
        ]

    def clean(self) -> None:
        super().clean()
        if self.left_listing_id and self.right_listing_id:
            if str(self.left_listing_id) >= str(self.right_listing_id):
                raise ValidationError("Duplicate candidate listing IDs must use canonical order.")

    def __str__(self) -> str:
        return f"{self.left_listing_id} ↔ {self.right_listing_id}: {self.final_score}"


class ListingCluster(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    status = models.CharField(
        max_length=16,
        choices=ClusterStatus.choices,
        default=ClusterStatus.ACTIVE,
        db_index=True,
    )
    primary_listing = models.ForeignKey(
        Listing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="primary_for_duplicate_clusters",
    )
    member_count = models.PositiveIntegerField(default=0)
    source_count = models.PositiveIntegerField(default=0)
    confidence_min = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    confidence_max = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    algorithm_version = models.PositiveSmallIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-updated_at",)

    def __str__(self) -> str:
        return f"Cluster {self.id} · {self.member_count} listings"


class ListingClusterMember(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cluster = models.ForeignKey(
        ListingCluster,
        on_delete=models.CASCADE,
        related_name="members",
    )
    listing = models.OneToOneField(
        Listing,
        on_delete=models.CASCADE,
        related_name="cluster_membership",
    )
    role = models.CharField(
        max_length=16,
        choices=ClusterMemberRole.choices,
        default=ClusterMemberRole.DUPLICATE,
    )
    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=100)
    joined_by = models.CharField(
        max_length=16,
        choices=ClusterJoinMethod.choices,
        default=ClusterJoinMethod.AUTO,
    )
    reasons = models.JSONField(default=list, blank=True)
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("role", "-confidence", "joined_at")
        constraints = [
            models.UniqueConstraint(
                fields=("cluster",),
                condition=Q(role=ClusterMemberRole.PRIMARY),
                name="duplicate_cluster_one_primary",
            )
        ]
        indexes = [
            models.Index(fields=("cluster", "role"), name="dup_member_cluster_role_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.cluster_id}:{self.listing_id}:{self.role}"


class DuplicateDecision(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    candidate = models.ForeignKey(
        DuplicateCandidate,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decision_history",
    )
    left_listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="duplicate_decisions_left",
    )
    right_listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="duplicate_decisions_right",
    )
    action = models.CharField(max_length=24, choices=DecisionAction.choices)
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="duplicate_decisions",
    )
    note = models.CharField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(
                fields=("left_listing", "right_listing", "-created_at"),
                name="dup_decision_pair_idx",
            )
        ]

    def save(self, *args: Any, **kwargs: Any) -> None:
        if self.pk and type(self).objects.filter(pk=self.pk).exists():
            raise ValidationError("DuplicateDecision records are immutable.")
        super().save(*args, **kwargs)

    def __str__(self) -> str:
        return f"{self.action}: {self.left_listing_id} ↔ {self.right_listing_id}"


class UserClusterState(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="cluster_states",
    )
    cluster = models.ForeignKey(
        ListingCluster,
        on_delete=models.CASCADE,
        related_name="user_states",
    )
    is_favorite = models.BooleanField(default=False, db_index=True)
    is_hidden = models.BooleanField(default=False, db_index=True)
    is_compared = models.BooleanField(default=False, db_index=True)
    note = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=("user", "cluster"),
                name="cluster_state_user_unique",
            )
        ]
        indexes = [
            models.Index(fields=("user", "is_favorite"), name="cluster_state_favorite_idx"),
            models.Index(fields=("user", "is_compared"), name="cluster_state_compare_idx"),
            models.Index(fields=("user", "is_hidden"), name="cluster_state_hidden_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.user_id}:{self.cluster_id}"
