from __future__ import annotations

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from apps.telegram_bot.handlers import router


def create_bot(token: str) -> Bot:
    return Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


def create_dispatcher(*, mini_app_url: str = "") -> Dispatcher:
    dispatcher = Dispatcher()
    dispatcher["mini_app_url"] = mini_app_url
    dispatcher.include_router(router)
    return dispatcher
