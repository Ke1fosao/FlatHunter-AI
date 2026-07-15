from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

from tests.test_telegram_init_data import build_init_data


@pytest.mark.django_db
def test_telegram_auth_creates_profile_and_session(client, settings) -> None:
    settings.TELEGRAM_BOT_TOKEN = "123456:test-token"

    response = client.post(
        reverse("telegram-auth"),
        data={"initData": build_init_data(query_id="auth-query")},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["user"]["telegramId"] == 12345
    assert response.json()["csrfToken"]
    assert get_user_model().objects.count() == 1
    assert client.session.get("_auth_user_id")


@pytest.mark.django_db
def test_me_requires_authentication(client) -> None:
    response = client.get(reverse("me"))

    assert response.status_code == 403


@pytest.mark.django_db
def test_telegram_premium_does_not_grant_flathunter_premium_role(client, settings) -> None:
    settings.TELEGRAM_BOT_TOKEN = "123456:test-token"

    response = client.post(
        reverse("telegram-auth"),
        data={"initData": build_init_data(query_id="premium-query", is_premium=True)},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json()["user"]["role"] == "user"
