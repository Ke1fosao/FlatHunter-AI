from typing import Any

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.http import HttpRequest

from apps.accounts.models import TelegramProfile, User


@admin.register(User)
class FlatHunterUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "role", "is_active")

    def get_fieldsets(
        self,
        request: HttpRequest,
        obj: User | None = None,
    ) -> Any:
        fieldsets = list(super().get_fieldsets(request, obj))
        fieldsets.append(("FlatHunter", {"fields": ("role", "locale")}))
        return fieldsets


@admin.register(TelegramProfile)
class TelegramProfileAdmin(admin.ModelAdmin):
    list_display = ("telegram_id", "username", "first_name", "last_authenticated_at")
    search_fields = ("telegram_id", "username", "first_name", "last_name")
    readonly_fields = ("created_at", "last_authenticated_at")
