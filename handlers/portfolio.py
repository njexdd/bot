from __future__ import annotations

from aiogram import F, Router
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup

from keyboards.menu import main_menu_kb


router = Router()


@router.callback_query(F.data == "menu:portfolio")
async def portfolio(call: CallbackQuery) -> None:
    kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📸 Смотреть портфолио", url="https://ru.pinterest.com/crystalwithluv/_created/")],
            [InlineKeyboardButton(text="⬅️ Назад в меню", callback_data="menu:back_to_menu")]
        ]
    )
    await call.message.edit_text("Портфолио\nНажмите кнопку ниже:", reply_markup=kb)
    await call.answer()


@router.callback_query(F.data == "menu:back_to_menu")
async def back_to_menu(call: CallbackQuery) -> None:
    await call.message.edit_text("<b>Главное меню</b>", reply_markup=main_menu_kb())
    await call.answer()

