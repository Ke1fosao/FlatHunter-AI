from __future__ import annotations

from django.contrib import admin

from apps.ai_analysis.models import AIPromptVersion, AIRequest


@admin.register(AIPromptVersion)
class AIPromptVersionAdmin(admin.ModelAdmin):
    list_display = ("feature", "version", "provider", "model", "is_active", "created_at")
    list_filter = ("provider", "is_active")
    search_fields = ("feature", "version", "prompt_checksum")


@admin.register(AIRequest)
class AIRequestAdmin(admin.ModelAdmin):
    list_display = ("feature", "provider", "model", "status", "latency_ms", "created_at")
    list_filter = ("provider", "status", "feature")
    search_fields = ("feature", "input_summary", "error_message")
    readonly_fields = ("created_at",)
