# Generated manually for Stage 8 AI analysis.

from __future__ import annotations

import uuid

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="AIPromptVersion",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("feature", models.CharField(max_length=80)),
                ("version", models.CharField(max_length=40)),
                ("provider", models.CharField(max_length=40)),
                ("model", models.CharField(blank=True, max_length=80)),
                ("prompt_checksum", models.CharField(max_length=64)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ("feature", "-created_at"),
            },
        ),
        migrations.CreateModel(
            name="AIRequest",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("feature", models.CharField(db_index=True, max_length=80)),
                ("provider", models.CharField(max_length=40)),
                ("model", models.CharField(blank=True, max_length=80)),
                ("prompt_version", models.CharField(max_length=40)),
                (
                    "status",
                    models.CharField(
                        choices=[("success", "Success"), ("fallback", "Fallback"), ("failed", "Failed")],
                        db_index=True,
                        default="success",
                        max_length=16,
                    ),
                ),
                ("input_summary", models.CharField(max_length=255)),
                ("output_data", models.JSONField(blank=True, default=dict)),
                ("error_message", models.CharField(blank=True, max_length=255)),
                ("latency_ms", models.PositiveIntegerField(default=0)),
                ("prompt_tokens", models.PositiveIntegerField(default=0)),
                ("completion_tokens", models.PositiveIntegerField(default=0)),
                ("total_tokens", models.PositiveIntegerField(default=0)),
                ("estimated_cost_usd", models.DecimalField(decimal_places=6, default=0, max_digits=10)),
                ("cache_key", models.CharField(blank=True, db_index=True, max_length=80)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "user",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="ai_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
            },
        ),
        migrations.AddConstraint(
            model_name="aipromptversion",
            constraint=models.UniqueConstraint(
                fields=("feature", "version", "provider"),
                name="ai_prompt_feature_version_provider_unique",
            ),
        ),
        migrations.AddIndex(
            model_name="aipromptversion",
            index=models.Index(fields=("feature", "is_active"), name="ai_prompt_feature_active_idx"),
        ),
        migrations.AddIndex(
            model_name="airequest",
            index=models.Index(fields=("feature", "created_at"), name="ai_request_feature_created_idx"),
        ),
        migrations.AddIndex(
            model_name="airequest",
            index=models.Index(fields=("provider", "status"), name="ai_request_provider_status_idx"),
        ),
    ]
