from __future__ import annotations

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from keyboards.menu import main_menu_kb


router = Router()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext) -> None:
    await state.clear()
    await message.answer(
        "<b>Привет!</b>\n"
        "Я бот для записи на маникюр.\n\n"
        "Выберите действие:",
        reply_markup=main_menu_kb(),
    )


@router.callback_query(F.data == "menu:back")
async def menu_back(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text(
        "<b>Главное меню</b>\nВыберите действие:",
        reply_markup=main_menu_kb(),
    )
    await call.answer()

