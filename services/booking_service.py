from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from aiogram import Bot

from config import Settings
from database.database import Database
from database.repository import BookingRepository, SlotRepository, UserRepository
from utils.formatter import format_booking_html
from utils.helpers import parse_phone


@dataclass(slots=True)
class BookingDraft:
    date: str
    slot_id: int
    time: str
    name: str
    phone: str


class BookingError(Exception):
    pass


class BookingService:
    def __init__(self, db: Database, bot: Bot, settings: Settings) -> None:
        self.db = db
        self.bot = bot
        self.settings = settings
        self.users = UserRepository(db)
        self.slots = SlotRepository(db)
        self.bookings = BookingRepository(db)

    async def user_has_booking(self, telegram_id: int) -> bool:
        user_id = await self.users.get_or_create(telegram_id)
        return (await self.bookings.get_user_booking(user_id)) is not None

    async def get_user_booking(self, telegram_id: int) -> Optional[dict]:
        user_id = await self.users.get_or_create(telegram_id)
        return await self.bookings.get_user_booking(user_id)

    async def validate_draft(self, draft: BookingDraft) -> BookingDraft:
        if not draft.name.strip():
            raise BookingError("Имя не может быть пустым.")
        phone = parse_phone(draft.phone)
        if not phone:
            raise BookingError("Введите корректный номер телефона.")
        slot = await self.slots.get_slot(draft.slot_id)
        if not slot:
            raise BookingError("Слот не найден. Попробуйте выбрать заново.")
        if int(slot["is_available"]) != 1:
            raise BookingError("Этот слот уже занят. Выберите другой.")
        if str(slot["date"]) != draft.date:
            raise BookingError("Некорректная дата слота.")
        draft.phone = phone
        draft.time = str(slot["time"])
        return draft

    async def create_booking(self, telegram_id: int, draft: BookingDraft) -> int:
        user_id = await self.users.get_or_create(telegram_id)
        existing = await self.bookings.get_user_booking(user_id)
        if existing:
            raise BookingError("У вас уже есть активная запись. Сначала отмените её в разделе «Моя запись».")

        slot = await self.slots.get_slot(draft.slot_id)
        if not slot or int(slot["is_available"]) != 1:
            raise BookingError("Слот уже недоступен. Выберите другой.")

        await self.users.update_profile(telegram_id, draft.name, draft.phone)
        await self.slots.mark_unavailable(draft.slot_id)

        try:
            booking_id = await self.bookings.create_booking(user_id, draft.slot_id)
        except Exception as e:
            # rollback slot availability if booking fails
            await self.slots.mark_available(draft.slot_id)
            raise BookingError("Не удалось создать запись. Попробуйте ещё раз.") from e

        await self._notify_admin_and_channel(telegram_id, booking_id)
        return booking_id

    async def cancel_user_booking(self, telegram_id: int) -> Optional[int]:
        user_id = await self.users.get_or_create(telegram_id)
        booking = await self.bookings.get_user_booking(user_id)
        if not booking:
            return None
        booking_id = int(booking["booking_id"])
        slot_id = int(booking["slot_id"])
        await self.bookings.delete_booking(booking_id)
        await self.slots.mark_available(slot_id)
        return booking_id

    async def admin_cancel_booking(self, booking_id: int) -> Optional[int]:
        booking = await self.bookings.get_booking_by_id(booking_id)
        if not booking:
            return None
        slot_id = int(booking["slot_id"])
        await self.bookings.delete_booking(booking_id)
        await self.slots.mark_available(slot_id)
        return slot_id

    async def _notify_admin_and_channel(self, telegram_id: int, booking_id: int) -> None:
        booking = await self.bookings.get_booking_by_id(booking_id)
        user = await self.users.get_by_telegram_id(telegram_id)
        if not booking or not user:
            return

        text = format_booking_html(
            date=str(booking["date"]),
            time=str(booking["time"]),
            name=str(user.get("name") or ""),
            phone=str(user.get("phone") or ""),
            telegram_id=telegram_id,
        )

        await self.bot.send_message(chat_id=self.settings.admin_id, text=f"<b>Новая запись</b>\n\n{text}")
        if self.settings.channel_id:
            await self.bot.send_message(chat_id=self.settings.channel_id, text=f"<b>Новая запись</b>\n\n{text}")

    @staticmethod
    def slot_datetime(date: str, time: str) -> datetime:
        return datetime.fromisoformat(f"{date}T{time}:00")

