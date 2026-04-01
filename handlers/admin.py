from __future__ import annotations

import re
from datetime import date, datetime, timedelta

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import CallbackQuery, Message, InlineKeyboardButton, InlineKeyboardMarkup

from database.repository import BookingRepository, SlotRepository, UserRepository
from keyboards.admin import AdminCB, admin_menu_kb, back_to_admin_kb
from keyboards.calendar import CalendarCB, build_calendar_kb
from services.booking_service import BookingService
from services.reminder_service import ReminderService
from utils.helpers import iso_in_days


router = Router()


class AdminStates(StatesGroup):
    waiting_day_date = State()
    waiting_slots = State()
    waiting_delete_slot_date = State()
    waiting_delete_slot_id = State()
    waiting_delete_confirm = State()
    waiting_close_day = State()
    waiting_cancel_booking = State()
    waiting_schedule = State()


TIME_RE = re.compile(r"^(?:[01]\d|2[0-3]):[0-5]\d$")


def _get_app(data: dict) -> object:
    return data["dispatcher"]["app"]


def _parse_date(s: str) -> str | None:
    try:
        return date.fromisoformat(s.strip()).isoformat()
    except Exception:
        return None


def _parse_times(s: str) -> list[str]:
    parts = re.split(r"[,\s]+", s.strip())
    out: list[str] = []
    for p in parts:
        if not p:
            continue
        if TIME_RE.match(p):
            out.append(p)
    return sorted(set(out))


@router.callback_query(F.data == "menu:admin")
async def admin_menu(call: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await call.message.edit_text("<b>Админ-панель</b>\nВыберите действие:", reply_markup=admin_menu_kb())
    await call.answer()


@router.callback_query(AdminCB.filter())
async def admin_actions(call: CallbackQuery, callback_data: AdminCB, state: FSMContext, **data) -> None:
    action = callback_data.action
    await state.clear()

    if action == "add_day":
        await state.set_state(AdminStates.waiting_day_date)
        today = date.today()
        end_date = iso_in_days(90)
        
        # Генерируем все даты на 90 дней вперед, чтобы кнопки в календаре были активны
        all_future_dates = {(today + timedelta(days=i)).isoformat() for i in range(90)}
        
        kb = build_calendar_kb(
            year=today.year,
            month=today.month,
            available_dates=all_future_dates,
            min_date=today,
            max_date=date.fromisoformat(end_date),
        )

        await call.message.edit_text(
            "Добавить рабочий день\n\nВыберите дату в календаре:\n"
            "Будут добавлены слоты по умолчанию: 10:00, 12:00, 14:00, 16:00, 18:00",
            reply_markup=kb,
        )
        await call.answer()
        return

    if action == "add_slots":
        await state.set_state(AdminStates.waiting_slots)
        await call.message.edit_text(
            "<b>Добавить временные слоты</b>\n\nОтправьте сообщение вида:\n"
            "<code>YYYY-MM-DD 10:00 12:00 14:00</code>\n"
            "Можно разделять временем пробелами или запятыми.",
            reply_markup=back_to_admin_kb(),
        )
        await call.answer()
        return

    if action == "delete_slot":
        await state.set_state(AdminStates.waiting_delete_slot_date)
        
        today = date.today()
        end_date = iso_in_days(90)
        # Генерируем все даты, чтобы админ мог выбрать любую для удаления слота
        all_future_dates = {(today + timedelta(days=i)).isoformat() for i in range(90)}
        
        kb = build_calendar_kb(
            year=today.year,
            month=today.month,
            available_dates=all_future_dates,
            min_date=today,
            max_date=date.fromisoformat(end_date),
        )
        await call.message.edit_text(
            "Удалить слот\n\nВыберите дату в календаре:",
            reply_markup=kb,
        )
        await call.answer()
        return

    if action == "ask_delete":
        slot_id = callback_data.slot_id
        app = _get_app(data)
        slot = await SlotRepository(app.db).get_slot(slot_id)
        
        if not slot:
            await call.answer("Слот не найден.")
            return

        kb = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=AdminCB(action="confirm_delete", slot_id=slot_id).pack()),
                InlineKeyboardButton(text="❌ Отмена", callback_data="menu:admin")
            ]
        ])
        
        await call.message.edit_text(
            f"⚠️ **Подтвердите удаление**\n\nДата: {slot['date']}\nВремя: {slot['time']}\n\n"
            "Внимание: если на этот слот был записан клиент, его запись также будет удалена!",
            reply_markup=kb
        )
        await call.answer()
        return

    if action == "confirm_delete":
        slot_id = callback_data.slot_id
        app = _get_app(data)
        slot_repo = SlotRepository(app.db)
        
        slot = await slot_repo.get_slot(slot_id) 
        if slot:
            await slot_repo.delete_slot(slot_id)
            await call.message.edit_text(
                f"✅ Слот {slot['date']} {slot['time']} успешно удален.",
                reply_markup=back_to_admin_kb()
            )
        else:
            await call.message.edit_text("Ошибка: слот не найден.", reply_markup=back_to_admin_kb())
        
        await state.clear()
        await call.answer()
        return
    
    if action == "confirm_delete_slot":
        slot_id = callback_data.slot_id
        app = _get_app(data)
        
        slot_repo = SlotRepository(app.db)
        slot = await slot_repo.get_slot(slot_id)
        
        if not slot:
            await call.answer("Слот уже удален или не найден.", show_alert=True)
            await call.message.edit_text("Админ-панель", reply_markup=admin_menu_kb())
            return
            
        await slot_repo.delete_slot(slot_id)
        
        await call.message.edit_text(
            f"✅ Слот на {slot['date']} в {slot['time']} успешно удален.", 
            reply_markup=back_to_admin_kb()
        )
        await call.answer()
        return

    if action == "close_day":
        await state.set_state(AdminStates.waiting_close_day)
        await call.message.edit_text(
            "<b>Закрыть день</b>\n\nОтправьте дату в формате <code>YYYY-MM-DD</code>.\n"
            "Все слоты на эту дату будут помечены как недоступные.",
            reply_markup=back_to_admin_kb(),
        )
        await call.answer()
        return

    if action == "cancel_booking":
        await state.set_state(AdminStates.waiting_cancel_booking)
        await call.message.edit_text(
            "<b>Отменить запись клиента</b>\n\nОтправьте <code>booking_id</code> (число).",
            reply_markup=back_to_admin_kb(),
        )
        await call.answer()
        return

    if action == "schedule":
        await state.set_state(AdminStates.waiting_schedule)
        await call.message.edit_text(
            "<b>Расписание на дату</b>\n\nОтправьте дату в формате <code>YYYY-MM-DD</code>.",
            reply_markup=back_to_admin_kb(),
        )
        await call.answer()
        return

    await call.answer("Неизвестное действие.", show_alert=True)


@router.callback_query(CalendarCB.filter(), AdminStates.waiting_day_date)
async def admin_add_day_calendar(call: CallbackQuery, callback_data: CalendarCB, state: FSMContext, **data) -> None:
    app = _get_app(data)
    today = date.today()
    max_d = date.fromisoformat(iso_in_days(90))
    year, month = callback_data.year, callback_data.month

    if callback_data.action == "prev":
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    elif callback_data.action == "next":
        month += 1
        if month == 13:
            month, year = 1, year + 1
    elif callback_data.action == "select":
        chosen = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
        times = ["10:00", "12:00", "14:00", "16:00", "18:00"]
        slots_repo = SlotRepository(app.db)
        await slots_repo.create_slots(chosen, times)
        await state.clear()
        await call.message.edit_text(f"✅ Готово. Слоты на {chosen} добавлены.", reply_markup=back_to_admin_kb())
        await call.answer()
        return
    else:
        await call.answer()
        return

    # Обновляем календарь при перелистывании месяцев
    all_future_dates = {(today + timedelta(days=i)).isoformat() for i in range(90)}
    kb = build_calendar_kb(
        year=year,
        month=month,
        available_dates=all_future_dates,
        min_date=today,
        max_date=max_d
    )
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()


@router.callback_query(CalendarCB.filter(), AdminStates.waiting_delete_slot_date)
async def admin_delete_slot_calendar(call: CallbackQuery, callback_data: CalendarCB, state: FSMContext, **data) -> None:
    app = _get_app(data)
    today = date.today()
    max_d = date.fromisoformat(iso_in_days(90))
    year, month = callback_data.year, callback_data.month

    if callback_data.action == "prev":
        month -= 1
        if month == 0:
            month, year = 12, year - 1
    elif callback_data.action == "next":
        month += 1
        if month == 13:
            month, year = 1, year + 1
    elif callback_data.action == "select":
        chosen = date(callback_data.year, callback_data.month, callback_data.day).isoformat()
        slots_repo = SlotRepository(app.db)
        slots = await slots_repo.get_slots_by_date(chosen) # [cite: 29, 30]
        
        if not slots:
            await call.answer("На эту дату нет слотов.", show_alert=True)
            return

        await state.set_state(AdminStates.waiting_delete_confirm) # Переходим к подтверждению
        
        rows = []
        for s in slots:
            # При нажатии на слот теперь вызываем действие 'ask_delete'
            rows.append([
                InlineKeyboardButton(
                    text=f"🗑 {s['time']}", 
                    callback_data=AdminCB(action="ask_delete", slot_id=int(s["id"])).pack()
                )
            ])
        
        rows.append([InlineKeyboardButton(text="⬅️ Назад", callback_data=AdminCB(action="delete_slot").pack())])
        await call.message.edit_text(f"Выберите слот на {chosen} для удаления:", reply_markup=InlineKeyboardMarkup(inline_keyboard=rows))
        await call.answer()
        return
    else:
        await call.answer()
        return

    # Перерисовка календаря при смене месяца
    all_future_dates = {(today + timedelta(days=i)).isoformat() for i in range(90)}
    kb = build_calendar_kb(
        year=year,
        month=month,
        available_dates=all_future_dates,
        min_date=today,
        max_date=max_d
    )
    await call.message.edit_reply_markup(reply_markup=kb)
    await call.answer()

@router.message(AdminStates.waiting_slots)
async def admin_add_slots(message: Message, state: FSMContext, **data) -> None:
    app = _get_app(data)
    text = (message.text or "").strip()
    if not text:
        await message.answer("Пустое сообщение.", reply_markup=back_to_admin_kb())
        return
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("Нужно: <code>YYYY-MM-DD</code> и список времён.", reply_markup=back_to_admin_kb())
        return
    d = _parse_date(parts[0])
    if not d:
        await message.answer("Неверная дата. Пример: <code>2026-03-18</code>", reply_markup=back_to_admin_kb())
        return
    times = _parse_times(parts[1])
    if not times:
        await message.answer("Не нашёл корректных времён. Пример: <code>10:00 12:00 14:00</code>", reply_markup=back_to_admin_kb())
        return
    slots_repo = SlotRepository(app.db)
    await slots_repo.create_slots(d, times)
    await state.clear()
    await message.answer(f"Готово. Слоты добавлены на <b>{d}</b>: <b>{', '.join(times)}</b>", reply_markup=back_to_admin_kb())


@router.message(AdminStates.waiting_close_day)
async def admin_close_day(message: Message, state: FSMContext, **data) -> None:
    app = _get_app(data)
    d = _parse_date(message.text or "")
    if not d:
        await message.answer("Неверная дата. Пример: <code>2026-03-18</code>", reply_markup=back_to_admin_kb())
        return
    await SlotRepository(app.db).set_day_availability(d, is_available=False)
    await state.clear()
    await message.answer(f"День <b>{d}</b> закрыт (слоты недоступны).", reply_markup=back_to_admin_kb())


@router.message(AdminStates.waiting_cancel_booking)
async def admin_cancel_booking(message: Message, state: FSMContext, **data) -> None:
    app = _get_app(data)
    try:
        booking_id = int((message.text or "").strip())
    except Exception:
        await message.answer("Нужно число <code>booking_id</code>.", reply_markup=back_to_admin_kb())
        return

    booking_repo = BookingRepository(app.db)
    booking = await booking_repo.get_booking_by_id(booking_id)
    if not booking:
        await message.answer("Запись не найдена.", reply_markup=back_to_admin_kb())
        return

    user_row = await app.db.fetchone(
        """
        SELECT u.telegram_id AS telegram_id
        FROM bookings b
        JOIN users u ON u.id = b.user_id
        WHERE b.id = ?;
        """,
        [booking_id],
    )
    user_tg_id = int(user_row["telegram_id"]) if user_row else None

    reminder_service = ReminderService(app.scheduler, app.db, app.bot)
    await reminder_service.cancel_for_booking(booking_id)
    await BookingService(app.db, app.bot, app.settings).admin_cancel_booking(booking_id)

    if user_tg_id:
        await app.bot.send_message(chat_id=user_tg_id, text="Ваша запись была отменена администратором. Вы можете записаться заново.")

    await state.clear()
    await message.answer(f"Запись <b>{booking_id}</b> отменена.", reply_markup=back_to_admin_kb())


@router.message(AdminStates.waiting_schedule)
async def admin_schedule(message: Message, state: FSMContext, **data) -> None:
    app = _get_app(data)
    d = _parse_date(message.text or "")
    if not d:
        await message.answer("Неверная дата. Пример: <code>2026-03-18</code>", reply_markup=back_to_admin_kb())
        return

    rows = await app.db.fetchall(
        """
        SELECT
            s.id AS slot_id,
            s.time AS time,
            s.is_available AS is_available,
            b.id AS booking_id,
            u.name AS name,
            u.phone AS phone
        FROM slots s
        LEFT JOIN bookings b ON b.slot_id = s.id
        LEFT JOIN users u ON u.id = b.user_id
        WHERE s.date = ?
        ORDER BY s.time ASC;
        """,
        [d],
    )

    if not rows:
        await message.answer(f"На дату <b>{d}</b> слотов нет.", reply_markup=back_to_admin_kb())
        return

    lines = [f"<b>Расписание на {d}</b>\n"]
    for r in rows:
        slot_id = int(r["slot_id"])
        time = str(r["time"])
        booking_id = r["booking_id"]
        if booking_id:
            name = str(r["name"] or "")
            phone = str(r["phone"] or "")
            lines.append(f"❌ <b>{time}</b> — занято (slot_id={slot_id}, booking_id={int(booking_id)})\n{name} / {phone}")
        else:
            is_av = int(r["is_available"]) == 1
            mark = "✅" if is_av else "⛔"
            lines.append(f"{mark} <b>{time}</b> — свободно (slot_id={slot_id})")

    await state.clear()
    await message.answer("\n".join(lines), reply_markup=back_to_admin_kb())

