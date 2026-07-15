from __future__ import annotations

import uuid

from django.contrib.auth.models import AbstractUser
from django.db import models


class UserRole(models.TextChoices):
    USER = "user", "Користувач"
    PREMIUM = "premium", "Premium"
    MODERATOR = "moderator", "Модератор"
    ADMIN = "admin", "Адміністратор"
    DEVELOPER = "developer", "Розробник"


class User(AbstractUser):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role = models.CharField(max_length=24, choices=UserRole.choices, default=UserRole.USER)
    locale = models.CharField(max_length=8, default="uk")


class TelegramProfile(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="telegram_profile")
    telegram_id = models.BigIntegerField(unique=True, db_index=True)
    username = models.CharField(max_length=64, blank=True)
    first_name = models.CharField(max_length=255, blank=True)
    last_name = models.CharField(max_length=255, blank=True)
    language_code = models.CharField(max_length=16, blank=True)
    is_premium = models.BooleanField(default=False)
    allows_write_to_pm = models.BooleanField(default=False)
    last_authenticated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self) -> str:
        return f"Telegram {self.telegram_id}"
