from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    Message,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    WebAppInfo,
)
from asgiref.sync import sync_to_async

router = Router(name=__name__)


class SearchOnboarding(StatesGroup):
    city = State()
    price_max = State()
    rooms = State()
    confirmation = State()


def build_start_keyboard(mini_app_url: str) -> InlineKeyboardMarkup:
    first_button = (
        InlineKeyboardButton(text="📱 Відкрити застосунок", web_app=WebAppInfo(url=mini_app_url))
        if mini_app_url
        else InlineKeyboardButton(
            text="📱 Застосунок налаштовується", callback_data="app_unavailable"
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


def onboarding_keyboard(*, allow_skip: bool = False) -> ReplyKeyboardMarkup:
    rows = [[KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Скасувати")]]
    if allow_skip:
        rows.insert(0, [KeyboardButton(text="⏭ Пропустити")])
    rows.append([KeyboardButton(text="⚙️ Розширені налаштування")])
    return ReplyKeyboardMarkup(
        keyboard=rows, resize_keyboard=True, input_field_placeholder="Введіть відповідь"
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


@router.callback_query(F.data == "create_search")
async def create_search(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await state.set_state(SearchOnboarding.city)
    if callback.message:
        await callback.message.answer(
            "У якому місті шукаємо житло?", reply_markup=onboarding_keyboard()
        )
    await callback.answer()


@router.message(F.text == "❌ Скасувати")
async def cancel_onboarding(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer("Створення пошуку скасовано.", reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "⚙️ Розширені налаштування")
async def open_advanced(message: Message, mini_app_url: str = "") -> None:
    if mini_app_url:
        keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(
                        text="Відкрити Mini App", web_app=WebAppInfo(url=mini_app_url)
                    )
                ]
            ]
        )
        await message.answer(
            "Розширені фільтри зручніше налаштувати у Mini App.", reply_markup=keyboard
        )
    else:
        await message.answer("Mini App ще не налаштований. Продовжимо короткий onboarding у боті.")


@router.message(SearchOnboarding.city)
async def receive_city(message: Message, state: FSMContext) -> None:
    if not message.text or message.text.startswith(("⬅️", "⏭")):
        await message.answer("Напишіть назву міста, наприклад: Львів.")
        return
    await state.update_data(city=message.text.strip())
    await state.set_state(SearchOnboarding.price_max)
    await message.answer(
        "Який максимальний бюджет на місяць у гривнях?", reply_markup=onboarding_keyboard()
    )


@router.message(SearchOnboarding.price_max)
async def receive_price(message: Message, state: FSMContext) -> None:
    raw = (message.text or "").replace(" ", "")
    if not raw.isdigit() or int(raw) < 1000:
        await message.answer("Введіть суму числом, наприклад 18000.")
        return
    await state.update_data(price_max=int(raw))
    await state.set_state(SearchOnboarding.rooms)
    await message.answer(
        "Скільки кімнат потрібно? Наприклад: 1 або 1,2.", reply_markup=onboarding_keyboard()
    )


@router.message(SearchOnboarding.rooms)
async def receive_rooms(message: Message, state: FSMContext) -> None:
    try:
        rooms = sorted(
            {int(value.strip()) for value in (message.text or "").split(",") if value.strip()}
        )
    except ValueError:
        rooms = []
    if not rooms or any(room < 1 or room > 10 for room in rooms):
        await message.answer("Вкажіть від 1 до 10 кімнат. Для кількох варіантів: 1,2.")
        return
    await state.update_data(rooms=rooms)
    data = await state.get_data()
    await state.set_state(SearchOnboarding.confirmation)
    await message.answer(
        "Я зрозумів так:\n\n"
        f"• {data['city']}\n"
        f"• кімнати: {', '.join(map(str, rooms))}\n"
        f"• до {data['price_max']:,} грн\n"
        "• довгострокова оренда\n\n"
        "Напишіть «✅ Все правильно» для збереження або «⬅️ Назад».",
        reply_markup=ReplyKeyboardMarkup(
            keyboard=[
                [KeyboardButton(text="✅ Все правильно")],
                [KeyboardButton(text="⬅️ Назад"), KeyboardButton(text="❌ Скасувати")],
                [KeyboardButton(text="⚙️ Розширені налаштування")],
            ],
            resize_keyboard=True,
        ),
    )


@sync_to_async
def _save_profile(telegram_id: int, data: dict[str, object]) -> bool:
    from apps.accounts.models import TelegramProfile
    from apps.searches.models import NotificationPreference, SearchProfile

    telegram_profile = (
        TelegramProfile.objects.filter(telegram_id=telegram_id).select_related("user").first()
    )
    if telegram_profile is None:
        return False
    profile = SearchProfile.objects.create(
        user=telegram_profile.user,
        name=f"Оренда · {data['city']}",
        city=str(data["city"]),
        price_max=int(data["price_max"]),
        rooms=list(data["rooms"]),
    )
    NotificationPreference.objects.create(search_profile=profile)
    return True


@router.message(SearchOnboarding.confirmation, F.text == "✅ Все правильно")
async def confirm_search(message: Message, state: FSMContext) -> None:
    data = await state.get_data()
    saved = await _save_profile(message.from_user.id, data) if message.from_user else False
    await state.clear()
    text = (
        "✅ Пошук створено й активовано."
        if saved
        else (
            "✅ Дані зібрано. Відкрийте Mini App один раз для безпечної "
            "авторизації та збереження профілю."
        )
    )
    await message.answer(text, reply_markup=ReplyKeyboardRemove())


@router.message(F.text == "⬅️ Назад")
async def go_back(message: Message, state: FSMContext) -> None:
    current = await state.get_state()
    if current == SearchOnboarding.price_max.state:
        await state.set_state(SearchOnboarding.city)
        await message.answer("У якому місті шукаємо житло?")
    elif current in {SearchOnboarding.rooms.state, SearchOnboarding.confirmation.state}:
        await state.set_state(SearchOnboarding.price_max)
        await message.answer("Який максимальний бюджет на місяць у гривнях?")
    else:
        await state.clear()
        await message.answer("Повернулися до головного меню.", reply_markup=ReplyKeyboardRemove())
