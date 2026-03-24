from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class AdminCB(CallbackData, prefix="adm"):
    action: str
    date: str = ""  # YYYY-MM-DD
    slot_id: int = 0
    booking_id: int = 0


def admin_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить рабочий день", callback_data=AdminCB(action="add_day").pack())],
            [InlineKeyboardButton(text="➕ Добавить слоты на дату", callback_data=AdminCB(action="add_slots").pack())],
            [InlineKeyboardButton(text="❌ Удалить слот", callback_data=AdminCB(action="delete_slot").pack())],
            [InlineKeyboardButton(text="❌ Закрыть день", callback_data=AdminCB(action="close_day").pack())],
            [InlineKeyboardButton(text="❌ Отменить запись клиента", callback_data=AdminCB(action="cancel_booking").pack())],
            [InlineKeyboardButton(text="📅 Расписание на дату", callback_data=AdminCB(action="schedule").pack())],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")],
        ]
    )


def back_to_admin_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="⬅️ Назад в админку", callback_data="menu:admin")]])

