from __future__ import annotations

import calendar
from datetime import date

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


class CalendarCB(CallbackData, prefix="cal"):
    action: str  # prev|next|select|noop
    year: int
    month: int
    day: int = 0


WEEKDAYS = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
MONTHS_RU = [
    "",
    "Январь",
    "Февраль",
    "Март",
    "Апрель",
    "Май",
    "Июнь",
    "Июль",
    "Август",
    "Сентябрь",
    "Октябрь",
    "Ноябрь",
    "Декабрь",
]


def build_calendar_kb(
    *,
    year: int,
    month: int,
    available_dates: set[str],
    min_date: date,
    max_date: date,
) -> InlineKeyboardMarkup:
    cal = calendar.Calendar(firstweekday=0)  # Monday
    month_days = cal.monthdayscalendar(year, month)

    header = InlineKeyboardButton(text=f"{MONTHS_RU[month]} {year}", callback_data=CalendarCB(action="noop", year=year, month=month).pack())
    prev_btn = InlineKeyboardButton(text="◀️", callback_data=CalendarCB(action="prev", year=year, month=month).pack())
    next_btn = InlineKeyboardButton(text="▶️", callback_data=CalendarCB(action="next", year=year, month=month).pack())

    kb: list[list[InlineKeyboardButton]] = []
    kb.append([prev_btn, header, next_btn])
    kb.append([InlineKeyboardButton(text=wd, callback_data=CalendarCB(action="noop", year=year, month=month).pack()) for wd in WEEKDAYS])

    for week in month_days:
        row: list[InlineKeyboardButton] = []
        for day in week:
            if day == 0:
                row.append(InlineKeyboardButton(text=" ", callback_data=CalendarCB(action="noop", year=year, month=month).pack()))
                continue

            d = date(year, month, day)
            if d < min_date or d > max_date:
                row.append(InlineKeyboardButton(text="·", callback_data=CalendarCB(action="noop", year=year, month=month).pack()))
                continue

            iso = d.isoformat()
            if iso not in available_dates:
                row.append(InlineKeyboardButton(text=str(day), callback_data=CalendarCB(action="empty_date", year=year, month=month).pack()))
                continue

            row.append(InlineKeyboardButton(text=f"{day}", callback_data=CalendarCB(action="select", year=year, month=month, day=day).pack()))
        kb.append(row)

    kb.append([InlineKeyboardButton(text="Назад", callback_data="menu:back")])
    return InlineKeyboardMarkup(inline_keyboard=kb)

