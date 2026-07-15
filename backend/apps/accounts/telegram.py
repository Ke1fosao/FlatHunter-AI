from __future__ import annotations

import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import parse_qsl

from django.core.cache import cache


class TelegramInitDataError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class TelegramWebAppUser:
    id: int
    first_name: str
    last_name: str = ""
    username: str = ""
    language_code: str = ""
    is_premium: bool = False
    allows_write_to_pm: bool = False


@dataclass(frozen=True, slots=True)
class ValidatedTelegramInitData:
    user: TelegramWebAppUser
    auth_date: int
    query_id: str
    hash_value: str
    start_param: str = ""


class TelegramInitDataValidator:
    def __init__(
        self,
        bot_token: str,
        *,
        max_age_seconds: int = 300,
        future_tolerance_seconds: int = 30,
        replay_ttl_seconds: int | None = None,
    ) -> None:
        if not bot_token:
            raise TelegramInitDataError("Telegram bot token is not configured")
        self.bot_token = bot_token
        self.max_age_seconds = max_age_seconds
        self.future_tolerance_seconds = future_tolerance_seconds
        self.replay_ttl_seconds = replay_ttl_seconds or max_age_seconds

    def validate(self, raw_init_data: str) -> ValidatedTelegramInitData:
        if not raw_init_data or len(raw_init_data) > 16_384:
            raise TelegramInitDataError("Telegram init data is missing or too large")

        try:
            pairs = parse_qsl(raw_init_data, keep_blank_values=True, strict_parsing=True)
        except ValueError as exc:
            raise TelegramInitDataError("Telegram init data is malformed") from exc

        keys = [key for key, _ in pairs]
        if len(keys) != len(set(keys)):
            raise TelegramInitDataError("Telegram init data contains duplicate fields")

        data = dict(pairs)
        received_hash = data.pop("hash", "")
        data.pop("signature", None)
        if not received_hash:
            raise TelegramInitDataError("Telegram signature is missing")

        data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
        secret_key = hmac.new(b"WebAppData", self.bot_token.encode(), hashlib.sha256).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(received_hash, expected_hash):
            raise TelegramInitDataError("Telegram signature is invalid")

        auth_date = self._parse_auth_date(data.get("auth_date"))
        self._check_freshness(auth_date)
        user = self._parse_user(data.get("user"))

        replay_key = f"telegram:init-data:{received_hash}"
        if not cache.add(replay_key, "used", timeout=self.replay_ttl_seconds):
            raise TelegramInitDataError("Telegram init data was already used")

        return ValidatedTelegramInitData(
            user=user,
            auth_date=auth_date,
            query_id=data.get("query_id", ""),
            hash_value=received_hash,
            start_param=data.get("start_param", ""),
        )

    def _parse_auth_date(self, value: str | None) -> int:
        try:
            return int(value or "")
        except ValueError as exc:
            raise TelegramInitDataError("Telegram auth_date is invalid") from exc

    def _check_freshness(self, auth_date: int) -> None:
        age = int(time.time()) - auth_date
        if age > self.max_age_seconds:
            raise TelegramInitDataError("Telegram init data has expired")
        if age < -self.future_tolerance_seconds:
            raise TelegramInitDataError("Telegram init data is from the future")

    def _parse_user(self, value: str | None) -> TelegramWebAppUser:
        if not value:
            raise TelegramInitDataError("Telegram user data is missing")
        try:
            payload: dict[str, Any] = json.loads(value)
            telegram_id = int(payload["id"])
            first_name = str(payload["first_name"])
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise TelegramInitDataError("Telegram user data is invalid") from exc

        return TelegramWebAppUser(
            id=telegram_id,
            first_name=first_name,
            last_name=str(payload.get("last_name", "")),
            username=str(payload.get("username", "")),
            language_code=str(payload.get("language_code", "")),
            is_premium=bool(payload.get("is_premium", False)),
            allows_write_to_pm=bool(payload.get("allows_write_to_pm", False)),
        )
