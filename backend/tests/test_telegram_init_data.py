from __future__ import annotations

import hashlib
import hmac
import json
import time
from urllib.parse import urlencode

import pytest
from django.core.cache import cache

from apps.accounts.telegram import TelegramInitDataError, TelegramInitDataValidator

BOT_TOKEN = "123456:test-token"


def build_init_data(
    *,
    auth_date: int | None = None,
    user_id: int = 12345,
    query_id: str = "query-1",
    is_premium: bool = False,
) -> str:
    data = {
        "auth_date": str(auth_date or int(time.time())),
        "query_id": query_id,
        "user": json.dumps(
            {
                "id": user_id,
                "first_name": "Дмитро",
                "last_name": "Ковтунович",
                "username": "ke1fosao",
                "language_code": "uk",
                "is_premium": is_premium,
            },
            ensure_ascii=False,
            separators=(",", ":"),
        ),
    }
    data_check_string = "\n".join(f"{key}={value}" for key, value in sorted(data.items()))
    secret_key = hmac.new(b"WebAppData", BOT_TOKEN.encode(), hashlib.sha256).digest()
    data["hash"] = hmac.new(secret_key, data_check_string.encode(), hashlib.sha256).hexdigest()
    return urlencode(data)


@pytest.fixture(autouse=True)
def clear_cache() -> None:
    cache.clear()


def test_accepts_valid_init_data() -> None:
    result = TelegramInitDataValidator(BOT_TOKEN, max_age_seconds=300).validate(build_init_data())

    assert result.user.id == 12345
    assert result.user.first_name == "Дмитро"
    assert result.query_id == "query-1"


def test_rejects_tampered_user_data() -> None:
    payload = build_init_data().replace("ke1fosao", "attacker")

    with pytest.raises(TelegramInitDataError, match="signature"):
        TelegramInitDataValidator(BOT_TOKEN).validate(payload)


def test_rejects_expired_auth_date() -> None:
    payload = build_init_data(auth_date=int(time.time()) - 301)

    with pytest.raises(TelegramInitDataError, match="expired"):
        TelegramInitDataValidator(BOT_TOKEN, max_age_seconds=300).validate(payload)


def test_rejects_replayed_payload() -> None:
    payload = build_init_data(query_id="same-query")
    validator = TelegramInitDataValidator(BOT_TOKEN)

    validator.validate(payload)

    with pytest.raises(TelegramInitDataError, match="already used"):
        validator.validate(payload)
