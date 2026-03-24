from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.menu import main_menu_kb
from services.booking_service import BookingService
from services.reminder_service import ReminderService


router = Router()


def _get_app(data: dict) -> object:
    return data["dispatcher"]["app"]


def _my_booking_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отменить", callback_data="my:cancel")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="menu:back")],
        ]
    )


@router.callback_query(F.data == "menu:my_booking")
async def show_my_booking(call: CallbackQuery, **data) -> None:
    app = _get_app(data)
    service = BookingService(app.db, app.bot, app.settings)
    booking = await service.get_user_booking(call.from_user.id)
    if not booking:
        await call.message.edit_text("У вас нет активной записи.", reply_markup=main_menu_kb())
        await call.answer()
        return

    text = (
        "<b>Ваша запись</b>\n\n"
        f"<b>Дата:</b> {booking['date']}\n"
        f"<b>Время:</b> {booking['time']}\n"
    )
    await call.message.edit_text(text, reply_markup=_my_booking_kb())
    await call.answer()


@router.callback_query(F.data == "my:cancel")
async def cancel_my_booking(call: CallbackQuery, **data) -> None:
    app = _get_app(data)
    service = BookingService(app.db, app.bot, app.settings)
    reminder_service = ReminderService(app.scheduler, app.db, app.bot)

    booking = await service.get_user_booking(call.from_user.id)
    if not booking:
        await call.answer("Активной записи нет.", show_alert=True)
        await call.message.edit_text("У вас нет активной записи.", reply_markup=main_menu_kb())
        return

    booking_id = int(booking["booking_id"])
    await reminder_service.cancel_for_booking(booking_id)
    await service.cancel_user_booking(call.from_user.id)

    await call.message.edit_text("Запись отменена. Слот снова доступен.", reply_markup=main_menu_kb())
    await call.answer()

