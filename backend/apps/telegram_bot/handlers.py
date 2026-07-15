from __future__ import annotations

from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message, WebAppInfo

router = Router(name=__name__)


def build_start_keyboard(mini_app_url: str) -> InlineKeyboardMarkup:
    first_button = (
        InlineKeyboardButton(text="📱 Відкрити застосунок", web_app=WebAppInfo(url=mini_app_url))
        if mini_app_url
        else InlineKeyboardButton(
            text="📱 Застосунок налаштовується",
            callback_data="app_unavailable",
        )
    )
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔎 Створити пошук", callback_data="create_search")],
            [first_button],
            [InlineKeyboardButton(text="✨ Подивитися демо", callback_data="demo")],
            [InlineKeyboardButton(text="❓ Як це працює", callback_data="how_it_works")],
        ]
    )


@router.message(CommandStart())
async def start_handler(message: Message, mini_app_url: str = "") -> None:
    await message.answer(
        "🏠 <b>Привіт! Я FlatHunter AI.</b>\n\n"
        "Я шукаю нові квартири, порівнюю їх із твоїми вимогами, "
        "прибираю дублікати й повідомляю, коли з’являється справді хороший варіант.\n\n"
        "Тобі більше не потрібно щогодини перевіряти різні сайти.",
        reply_markup=build_start_keyboard(mini_app_url),
    )
