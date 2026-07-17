from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models


class AIRequestStatus(models.TextChoices):
    SUCCESS = "success", "Success"
    FALLBACK = "fallback", "Fallback"
    FAILED = "failed", "Failed"


class AIPromptVersion(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    feature = models.CharField(max_length=80)
    version = models.CharField(max_length=40)
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80, blank=True)
    prompt_checksum = models.CharField(max_length=64)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("feature", "-created_at")
        constraints = [
            models.UniqueConstraint(
                fields=("feature", "version", "provider"),
                name="ai_prompt_feature_version_provider_unique",
            )
        ]
        indexes = [
            models.Index(fields=("feature", "is_active"), name="ai_prompt_feature_active_idx")
        ]

    def __str__(self) -> str:
        return f"{self.feature}:{self.version}:{self.provider}"


class AIRequest(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="ai_requests",
    )
    feature = models.CharField(max_length=80, db_index=True)
    provider = models.CharField(max_length=40)
    model = models.CharField(max_length=80, blank=True)
    prompt_version = models.CharField(max_length=40)
    status = models.CharField(
        max_length=16,
        choices=AIRequestStatus.choices,
        default=AIRequestStatus.SUCCESS,
        db_index=True,
    )
    input_summary = models.CharField(max_length=255)
    output_data = models.JSONField(default=dict, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    latency_ms = models.PositiveIntegerField(default=0)
    prompt_tokens = models.PositiveIntegerField(default=0)
    completion_tokens = models.PositiveIntegerField(default=0)
    total_tokens = models.PositiveIntegerField(default=0)
    estimated_cost_usd = models.DecimalField(max_digits=10, decimal_places=6, default=0)
    cache_key = models.CharField(max_length=80, blank=True, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("feature", "created_at"), name="ai_request_feature_created_idx"),
            models.Index(fields=("provider", "status"), name="ai_request_provider_status_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.feature} {self.status} {self.provider}"
