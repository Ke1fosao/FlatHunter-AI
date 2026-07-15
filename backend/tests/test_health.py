from __future__ import annotations

import pytest
from django.urls import reverse


@pytest.mark.django_db
def test_liveness_endpoint(client) -> None:
    response = client.get(reverse("health-live"))

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "backend"}


@pytest.mark.django_db
def test_readiness_endpoint_checks_dependencies(client) -> None:
    response = client.get(reverse("health-ready"))

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ready"
    assert body["checks"]["database"] == "ok"
    assert body["checks"]["cache"] == "ok"
