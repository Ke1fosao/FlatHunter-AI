from __future__ import annotations

import uuid

from django.core.cache import cache
from django.db import connection
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET


def _dependency_checks() -> tuple[dict[str, str], bool]:
    checks: dict[str, str] = {}
    ready = True

    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"
        ready = False

    cache_key = f"health:{uuid.uuid4()}"
    try:
        cache.set(cache_key, "ok", timeout=5)
        checks["cache"] = "ok" if cache.get(cache_key) == "ok" else "error"
        cache.delete(cache_key)
        ready = ready and checks["cache"] == "ok"
    except Exception:
        checks["cache"] = "error"
        ready = False

    return checks, ready


@require_GET
def health_live(_request: HttpRequest) -> JsonResponse:
    return JsonResponse({"status": "ok", "service": "backend"})


@require_GET
def health_ready(_request: HttpRequest) -> JsonResponse:
    checks, ready = _dependency_checks()
    return JsonResponse(
        {"status": "ready" if ready else "not_ready", "checks": checks},
        status=200 if ready else 503,
    )


@require_GET
def health_api(_request: HttpRequest) -> JsonResponse:
    checks, ready = _dependency_checks()
    return JsonResponse(
        {
            "status": "ready" if ready else "degraded",
            "service": "flathunter-backend",
            "checks": checks,
        },
        status=200 if ready else 503,
    )
