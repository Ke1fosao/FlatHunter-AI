from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("listings", "0003_listing_location"),
    ]

    operations = [
        migrations.CreateModel(
            name="ListingCluster",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("status", models.CharField(choices=[("active", "Active"), ("split", "Split"), ("archived", "Archived")], db_index=True, default="active", max_length=16)),
                ("member_count", models.PositiveIntegerField(default=0)),
                ("source_count", models.PositiveIntegerField(default=0)),
                ("confidence_min", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("confidence_max", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("algorithm_version", models.PositiveSmallIntegerField(default=1)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("primary_listing", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="primary_for_duplicate_clusters", to="listings.listing")),
            ],
            options={"ordering": ("-updated_at",)},
        ),
        migrations.CreateModel(
            name="ListingFingerprint",
            fields=[
                ("listing", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, primary_key=True, related_name="duplicate_fingerprint", serialize=False, to="listings.listing")),
                ("version", models.PositiveSmallIntegerField(default=1)),
                ("normalized_city", models.CharField(db_index=True, max_length=120)),
                ("normalized_district", models.CharField(blank=True, max_length=120)),
                ("normalized_street", models.CharField(blank=True, max_length=160)),
                ("normalized_title", models.CharField(blank=True, max_length=500)),
                ("normalized_description", models.TextField(blank=True)),
                ("normalized_url", models.CharField(blank=True, db_index=True, max_length=500)),
                ("address_key", models.CharField(blank=True, db_index=True, max_length=320)),
                ("geo_block_key", models.CharField(blank=True, db_index=True, max_length=96)),
                ("attribute_key", models.CharField(blank=True, db_index=True, max_length=320)),
                ("price_bucket", models.PositiveIntegerField(db_index=True, default=0)),
                ("text_simhash", models.CharField(blank=True, max_length=16)),
                ("text_block_key", models.CharField(blank=True, db_index=True, max_length=64)),
                ("contact_hashes", models.JSONField(blank=True, default=list)),
                ("image_hashes", models.JSONField(blank=True, default=list)),
                ("image_hash_version", models.PositiveSmallIntegerField(default=1)),
                ("generated_at", models.DateTimeField(auto_now=True)),
                ("source_updated_at", models.DateTimeField()),
                ("last_error", models.CharField(blank=True, max_length=500)),
            ],
        ),
        migrations.CreateModel(
            name="DuplicateCandidate",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("exact_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("address_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("geo_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("attributes_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("text_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("image_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("price_score", models.DecimalField(blank=True, decimal_places=2, max_digits=5, null=True)),
                ("final_score", models.DecimalField(db_index=True, decimal_places=2, default=0, max_digits=5)),
                ("decision", models.CharField(choices=[("auto_merge", "Auto merge"), ("needs_review", "Needs review"), ("rejected", "Rejected"), ("confirmed", "Confirmed"), ("split", "Split / blocked")], db_index=True, default="rejected", max_length=24)),
                ("reasons", models.JSONField(blank=True, default=list)),
                ("hard_conflicts", models.JSONField(blank=True, default=list)),
                ("algorithm_version", models.PositiveSmallIntegerField(default=1)),
                ("evaluated_at", models.DateTimeField(auto_now=True)),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("review_note", models.CharField(blank=True, max_length=1000)),
                ("left_listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duplicate_candidates_left", to="listings.listing")),
                ("reviewed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="duplicate_candidate_reviews", to=settings.AUTH_USER_MODEL)),
                ("right_listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duplicate_candidates_right", to="listings.listing")),
            ],
            options={"ordering": ("-final_score", "left_listing_id", "right_listing_id")},
        ),
        migrations.CreateModel(
            name="DuplicateDecision",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("action", models.CharField(choices=[("confirm", "Confirm"), ("split", "Split"), ("block_pair", "Block pair"), ("restore_auto", "Restore automatic policy")], max_length=24)),
                ("note", models.CharField(blank=True, max_length=1000)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("actor", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="duplicate_decisions", to=settings.AUTH_USER_MODEL)),
                ("candidate", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="decision_history", to="duplicates.duplicatecandidate")),
                ("left_listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duplicate_decisions_left", to="listings.listing")),
                ("right_listing", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="duplicate_decisions_right", to="listings.listing")),
            ],
            options={"ordering": ("-created_at",)},
        ),
        migrations.CreateModel(
            name="ListingClusterMember",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("role", models.CharField(choices=[("primary", "Primary"), ("duplicate", "Duplicate")], default="duplicate", max_length=16)),
                ("confidence", models.DecimalField(decimal_places=2, default=100, max_digits=5)),
                ("joined_by", models.CharField(choices=[("auto", "Automatic"), ("manual", "Manual"), ("exact", "Exact rule")], default="auto", max_length=16)),
                ("reasons", models.JSONField(blank=True, default=list)),
                ("joined_at", models.DateTimeField(auto_now_add=True)),
                ("cluster", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="duplicates.listingcluster")),
                ("listing", models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="cluster_membership", to="listings.listing")),
            ],
            options={"ordering": ("role", "-confidence", "joined_at")},
        ),
        migrations.CreateModel(
            name="UserClusterState",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("is_favorite", models.BooleanField(db_index=True, default=False)),
                ("is_hidden", models.BooleanField(db_index=True, default=False)),
                ("is_compared", models.BooleanField(db_index=True, default=False)),
                ("note", models.CharField(blank=True, max_length=500)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("cluster", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="user_states", to="duplicates.listingcluster")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="cluster_states", to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddIndex(model_name="listingfingerprint", index=models.Index(fields=["normalized_city", "address_key"], name="dup_fp_city_address_idx")),
        migrations.AddIndex(model_name="listingfingerprint", index=models.Index(fields=["normalized_city", "attribute_key", "price_bucket"], name="dup_fp_attr_price_idx")),
        migrations.AddIndex(model_name="listingfingerprint", index=models.Index(fields=["normalized_city", "geo_block_key"], name="dup_fp_city_geo_idx")),
        migrations.AddConstraint(model_name="duplicatecandidate", constraint=models.UniqueConstraint(fields=("left_listing", "right_listing"), name="dup_candidate_pair_unique")),
        migrations.AddConstraint(model_name="duplicatecandidate", constraint=models.CheckConstraint(condition=~models.Q(left_listing=models.F("right_listing")), name="dup_candidate_distinct")),
        migrations.AddIndex(model_name="duplicatecandidate", index=models.Index(fields=["decision", "-final_score"], name="dup_candidate_decision_idx")),
        migrations.AddIndex(model_name="duplicatecandidate", index=models.Index(fields=["left_listing", "decision"], name="dup_candidate_left_idx")),
        migrations.AddIndex(model_name="duplicatecandidate", index=models.Index(fields=["right_listing", "decision"], name="dup_candidate_right_idx")),
        migrations.AddIndex(model_name="duplicatedecision", index=models.Index(fields=["left_listing", "right_listing", "-created_at"], name="dup_decision_pair_idx")),
        migrations.AddConstraint(model_name="listingclustermember", constraint=models.UniqueConstraint(condition=models.Q(role="primary"), fields=("cluster",), name="duplicate_cluster_one_primary")),
        migrations.AddIndex(model_name="listingclustermember", index=models.Index(fields=["cluster", "role"], name="dup_member_cluster_role_idx")),
        migrations.AddConstraint(model_name="userclusterstate", constraint=models.UniqueConstraint(fields=("user", "cluster"), name="cluster_state_user_unique")),
        migrations.AddIndex(model_name="userclusterstate", index=models.Index(fields=["user", "is_favorite"], name="cluster_state_favorite_idx")),
        migrations.AddIndex(model_name="userclusterstate", index=models.Index(fields=["user", "is_compared"], name="cluster_state_compare_idx")),
        migrations.AddIndex(model_name="userclusterstate", index=models.Index(fields=["user", "is_hidden"], name="cluster_state_hidden_idx")),
    ]
