from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_webhook_rejects_wrong_secret(client, settings) -> None:
    settings.TELEGRAM_WEBHOOK_SECRET = "expected-secret"

    response = client.post(
        reverse("telegram-webhook"),
        data={"update_id": 1},
        content_type="application/json",
        HTTP_X_TELEGRAM_BOT_API_SECRET_TOKEN="wrong-secret",
    )

    assert response.status_code == 403
