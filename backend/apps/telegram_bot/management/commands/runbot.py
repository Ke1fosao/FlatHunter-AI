from __future__ import annotations

import asyncio

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from apps.telegram_bot.runtime import create_bot, create_dispatcher


class Command(BaseCommand):
    help = "Run FlatHunter Telegram bot in long-polling mode"

    def handle(self, *args: object, **options: object) -> None:
        if settings.TELEGRAM_MODE != "polling":
            raise CommandError("TELEGRAM_MODE must be 'polling' to run this process")
        if not settings.TELEGRAM_BOT_TOKEN:
            raise CommandError("TELEGRAM_BOT_TOKEN is not configured")
        asyncio.run(self._run())

    async def _run(self) -> None:
        bot = create_bot(settings.TELEGRAM_BOT_TOKEN)
        dispatcher = create_dispatcher(mini_app_url=settings.TELEGRAM_MINI_APP_URL)
        try:
            await dispatcher.start_polling(
                bot,
                allowed_updates=dispatcher.resolve_used_update_types(),
            )
        finally:
            await bot.session.close()
