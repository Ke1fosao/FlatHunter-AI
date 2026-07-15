from __future__ import annotations

from django.db import transaction

from apps.accounts.models import TelegramProfile, User, UserRole
from apps.accounts.telegram import TelegramWebAppUser


@transaction.atomic
def get_or_create_telegram_user(data: TelegramWebAppUser) -> User:
    profile = TelegramProfile.objects.select_related("user").filter(telegram_id=data.id).first()
    if profile is None:
        user = User.objects.create_user(
            username=f"tg_{data.id}",
            first_name=data.first_name,
            last_name=data.last_name,
            locale=data.language_code or "uk",
            role=UserRole.USER,
        )
        user.set_unusable_password()
        user.save(update_fields=["password"])
        profile = TelegramProfile.objects.create(user=user, telegram_id=data.id)
    else:
        user = profile.user
        changed_fields: list[str] = []
        for field_name, value in (
            ("first_name", data.first_name),
            ("last_name", data.last_name),
            ("locale", data.language_code or user.locale),
        ):
            if getattr(user, field_name) != value:
                setattr(user, field_name, value)
                changed_fields.append(field_name)
        if changed_fields:
            user.save(update_fields=changed_fields)

    profile.username = data.username
    profile.first_name = data.first_name
    profile.last_name = data.last_name
    profile.language_code = data.language_code
    profile.is_premium = data.is_premium
    profile.allows_write_to_pm = data.allows_write_to_pm
    profile.save()
    return user
