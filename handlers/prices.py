from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery

from keyboards.menu import main_menu_kb


router = Router()


@router.callback_query(F.data == "menu:prices")
async def prices(call: CallbackQuery) -> None:
    text = "<b>Прайсы</b>\n\n" "Френч — <b>1000₽</b>\n" "Квадрат — <b>500₽</b>"
    await call.message.edit_text(text, reply_markup=main_menu_kb())
    await call.answer()

