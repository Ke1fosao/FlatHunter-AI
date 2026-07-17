from __future__ import annotations

import hmac
import json
import logging
from typing import Any

from asgiref.sync import sync_to_async
from django.conf import settings
from django.core.cache import cache
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET

logger = logging.getLogger(__name__)


@csrf_exempt
async def telegram_webhook(request: HttpRequest) -> JsonResponse:
    if request.method != "POST":
        return JsonResponse({"error": "method_not_allowed"}, status=405)

    provided_secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token", "")
    expected_secret = settings.TELEGRAM_WEBHOOK_SECRET
    if not expected_secret or not hmac.compare_digest(provided_secret, expected_secret):
        return JsonResponse({"error": "forbidden"}, status=403)

    try:
        payload: dict[str, Any] = json.loads(request.body)
        update_id = int(payload["update_id"])
    except (json.JSONDecodeError, KeyError, TypeError, ValueError):
        return JsonResponse({"error": "invalid_update"}, status=400)

    cache_key = f"telegram:update:{update_id}"
    accepted = await sync_to_async(cache.add)(cache_key, "processing", settings.TELEGRAM_UPDATE_TTL)
    if not accepted:
        return JsonResponse({"status": "duplicate"})

    if not settings.TELEGRAM_BOT_TOKEN:
        await sync_to_async(cache.delete)(cache_key)
        return JsonResponse({"error": "bot_not_configured"}, status=503)

    from aiogram.types import Update

    from apps.telegram_bot.runtime import create_bot, create_dispatcher

    bot = create_bot(settings.TELEGRAM_BOT_TOKEN)
    dispatcher = create_dispatcher(mini_app_url=settings.TELEGRAM_MINI_APP_URL)
    try:
        update = Update.model_validate(payload, context={"bot": bot})
        await dispatcher.feed_update(bot, update)
        await sync_to_async(cache.set)(cache_key, "processed", settings.TELEGRAM_UPDATE_TTL)
    except Exception:
        await sync_to_async(cache.delete)(cache_key)
        logger.exception("telegram_webhook_processing_failed", extra={"update_id": update_id})
        return JsonResponse({"error": "processing_failed"}, status=500)
    finally:
        await bot.session.close()

    return JsonResponse({"status": "ok"})


@require_GET
def telegram_status(_request: HttpRequest) -> JsonResponse:
    return JsonResponse(
        {
            "mode": settings.TELEGRAM_MODE,
            "botConfigured": bool(settings.TELEGRAM_BOT_TOKEN),
            "miniAppConfigured": bool(settings.TELEGRAM_MINI_APP_URL),
            "webhookConfigured": bool(
                settings.TELEGRAM_WEBHOOK_URL and settings.TELEGRAM_WEBHOOK_SECRET
            ),
        }
    )
