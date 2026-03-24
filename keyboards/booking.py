from __future__ import annotations

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class SlotCB(CallbackData, prefix="slot"):
    slot_id: int


class BookingActionCB(CallbackData, prefix="bookact"):
    action: str  # confirm|cancel|back_dates|back_times


def slots_kb(slots: list[dict]) -> InlineKeyboardMarkup:
    rows: list[list[InlineKeyboardButton]] = []
    for s in slots:
        rows.append([InlineKeyboardButton(text=str(s["time"]), callback_data=SlotCB(slot_id=int(s["id"])).pack())])
    rows.append([InlineKeyboardButton(text="Назад к датам", callback_data=BookingActionCB(action="back_dates").pack())])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Подтвердить", callback_data=BookingActionCB(action="confirm").pack()),
                InlineKeyboardButton(text="Отмена", callback_data=BookingActionCB(action="cancel").pack()),
            ],
            [InlineKeyboardButton(text="Назад к времени", callback_data=BookingActionCB(action="back_times").pack())],
        ]
    )

