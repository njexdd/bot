from __future__ import annotations

from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💅 Записаться", callback_data="menu:book")],
            [InlineKeyboardButton(text="🗓 Моя запись", callback_data="menu:my_booking")],
            [InlineKeyboardButton(text="💰 Прайсы", callback_data="menu:prices")],
            [InlineKeyboardButton(text="📸 Портфолио", callback_data="menu:portfolio")],
            [InlineKeyboardButton(text="⚙️ Админ-панель", callback_data="menu:admin")],
        ]
    )

