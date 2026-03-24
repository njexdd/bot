from __future__ import annotations

from datetime import date

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database.repository import SlotRepository
from keyboards.booking import BookingActionCB, SlotCB, confirm_kb, slots_kb
from keyboards.calendar import CalendarCB, build_calendar_kb
from keyboards.menu import main_menu_kb
from services.booking_service import BookingDraft, BookingError, BookingService
from services.reminder_service import ReminderService
from states.booking_states import BookingStates
from utils.helpers import iso_in_days, today_iso


router = Router()


def _get_app(data: dict) -> object:
    return data["dispatcher"]["app"]  # set in bot.py


@router.callback_query(F.data == "menu:book")
async def start_booking(call: CallbackQuery, state: FSMContext, **data) -> None:
    app = _get_app(data)
    service = BookingService(app.db, app.bot, app.settings)
    if await service.user_has_booking(call.from_user.id):
        await call.message.edit_text(
            "У вас уже есть активная запись.\nОткройте <b>«Моя запись»</b>, чтобы посмотреть или отменить её.",
            reply_markup=main_menu_kb(),
        )
        await call.answer()
        return

    start = today_iso()
    end = iso_in_days(30)
    slots_repo = SlotRepository(app.db)
    available_dates = set(await slots_repo.get_available_dates(start, end))

    today = date.today()
    await state.set_state(BookingStates.choosing_date)
    await state.update_data(cal_year=today.year, cal_month=today.month)

    kb = build_calendar_kb(
        year=today.year,
        month=today.month,
        available_dates=available_dates,
        min_date=today,
        max_date=date.fromisoformat(end),
    )
    await call.message.edit_text("<b>Выберите дату</b> (✅ — есть свободные слоты):", reply_markup=kb)
    await call.answer()


@router.callback_query(CalendarCB.filter(), BookingStates.choosing_date)
async def calendar_nav(call: CallbackQuery, callback_data: CalendarCB, state: FSMContext, **data) -> None:
    app = _get_app(data)
    start = today_iso()
    end = iso_in_days(30)
    slots_repo = SlotRepository(app.db)
    available_dates = set(await slots_repo.get_available_dates(start, end))

    today = date.today()
    max_d = date.fromisoformat(end)

    year, month = callback_data.year, callback_data.month
    if callback_data.action == "prev":
        month -= 1
        if month == 0:
            month = 12
            year -= 1
    elif callback_data.action == "next":
        month += 1
        if month == 13:
            month = 1
            year += 1
    elif callback_data.action == "select":
        chosen = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
        await state.update_data(chosen_date=chosen)
        await state.set_state(BookingStates.choosing_time)
        slots = await slots_repo.get_available_slots_by_date(chosen)
        if not slots:
            await call.answer("На эту дату нет свободных слотов.", show_alert=True)
            await state.set_state(BookingStates.choosing_date)
            return
        await call.message.edit_text(f"<b>Выберите время</b>\nДата: <b>{chosen}</b>", reply_markup=slots_kb(slots))
        await call.answer()
        return
    else:
        await call.answer()
        return

    kb = build_calendar_kb(year=year, month=month, available_dates=available_dates, min_date=today, max_date=max_d)
    await state.update_data(cal_year=year, cal_month=month)
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


@router.callback_query(SlotCB.filter(), BookingStates.choosing_time)
async def choose_slot(call: CallbackQuery, callback_data: SlotCB, state: FSMContext, **data) -> None:
    app = _get_app(data)
    slots_repo = SlotRepository(app.db)
    slot = await slots_repo.get_slot(callback_data.slot_id)
    if not slot or int(slot["is_available"]) != 1:
        await call.answer("Слот уже недоступен.", show_alert=True)
        return
    await state.update_data(slot_id=int(slot["id"]), time=str(slot["time"]), date=str(slot["date"]))
    await state.set_state(BookingStates.entering_name)
    await call.message.edit_text(
        f"<b>Введите имя</b>\nДата: <b>{slot['date']}</b>\nВремя: <b>{slot['time']}</b>\n\n"
        "Отправьте сообщение с вашим именем.",
        reply_markup=None,
    )
    await call.answer()


@router.message(BookingStates.entering_name)
async def enter_name(message: Message, state: FSMContext) -> None:
    name = (message.text or "").strip()
    if len(name) < 2:
        await message.answer("Пожалуйста, введите имя (минимум 2 символа).")
        return
    await state.update_data(name=name)
    await state.set_state(BookingStates.entering_phone)
    await message.answer("Введите номер телефона (например, +79991234567).")


@router.message(BookingStates.entering_phone)
async def enter_phone(message: Message, state: FSMContext, **data) -> None:
    phone = (message.text or "").strip()
    data_ = await state.get_data()
    draft = BookingDraft(
        date=str(data_.get("date")),
        slot_id=int(data_.get("slot_id")),
        time=str(data_.get("time")),
        name=str(data_.get("name")),
        phone=phone,
    )
    app = _get_app(data)
    service = BookingService(app.db, app.bot, app.settings)
    try:
        draft = await service.validate_draft(draft)
    except BookingError as e:
        await message.answer(str(e))
        return

    await state.update_data(phone=draft.phone, time=draft.time)
    await state.set_state(BookingStates.confirming)

    text = (
        "<b>Подтвердите запись</b>\n\n"
        f"<b>Дата:</b> {draft.date}\n"
        f"<b>Время:</b> {draft.time}\n"
        f"<b>Имя:</b> {draft.name}\n"
        f"<b>Телефон:</b> {draft.phone}\n"
    )
    await message.answer(text, reply_markup=confirm_kb())


@router.callback_query(BookingActionCB.filter(F.action == "back_dates"), BookingStates.choosing_time)
async def back_to_dates(call: CallbackQuery, state: FSMContext, **data) -> None:
    app = _get_app(data)
    start = today_iso()
    end = iso_in_days(30)
    available_dates = set(await SlotRepository(app.db).get_available_dates(start, end))
    today = date.today()
    kb = build_calendar_kb(
        year=today.year,
        month=today.month,
        available_dates=available_dates,
        min_date=today,
        max_date=date.fromisoformat(end),
    )
    await state.set_state(BookingStates.choosing_date)
    await call.message.edit_text("<b>Выберите дату</b> (✅ — есть свободные слоты):", reply_markup=kb)
    await call.answer()


@router.callback_query(BookingActionCB.filter(F.action == "back_times"), BookingStates.confirming)
async def back_to_times(call: CallbackQuery, state: FSMContext, **data) -> None:
    app = _get_app(data)
    data_ = await state.get_data()
    chosen_date = str(data_.get("date"))
    slots = await SlotRepository(app.db).get_available_slots_by_date(chosen_date)
    await state.set_state(BookingStates.choosing_time)
    await call.message.edit_text(f"<b>Выберите время</b>\nДата: <b>{chosen_date}</b>", reply_markup=slots_kb(slots))
    await call.answer()


@router.callback_query(BookingActionCB.filter(F.action == "cancel"), BookingStates.confirming)
async def booking_cancel(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("<b>Главное меню</b>", reply_markup=main_menu_kb())
    await call.answer()


@router.callback_query(BookingActionCB.filter(F.action == "confirm"), BookingStates.confirming)
async def booking_confirm(call: CallbackQuery, state: FSMContext, **data) -> None:
    app = _get_app(data)
    service = BookingService(app.db, app.bot, app.settings)
    reminder_service = ReminderService(app.scheduler, app.db, app.bot)

    data_ = await state.get_data()
    draft = BookingDraft(
        date=str(data_.get("date")),
        slot_id=int(data_.get("slot_id")),
        time=str(data_.get("time")),
        name=str(data_.get("name")),
        phone=str(data_.get("phone")),
    )

    try:
        draft = await service.validate_draft(draft)
        booking_id = await service.create_booking(call.from_user.id, draft)
    except BookingError as e:
        await call.answer(str(e), show_alert=True)
        return

    await reminder_service.schedule_for_booking(booking_id=booking_id, telegram_id=call.from_user.id)
    await state.clear()

    await call.message.edit_text(
        "<b>Готово!</b>\n"
        f"Вы записаны на <b>{draft.date}</b> в <b>{draft.time}</b>.\n\n"
        "Посмотреть или отменить запись можно в разделе <b>«Моя запись»</b>.",
        reply_markup=main_menu_kb(),
    )
    await call.answer()

