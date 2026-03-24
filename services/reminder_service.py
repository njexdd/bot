from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from aiogram import Bot

from database.database import Database
from database.repository import BookingRepository, ReminderRepository, SlotRepository, UserRepository
from services.scheduler_service import SchedulerService


REMINDER_TEXT_TEMPLATE = (
    "Напоминаем, что вы записаны на наращивание ресниц завтра в <b>{time}</b>.\n"
    "Ждём вас ❤️"
)


class ReminderService:
    def __init__(self, scheduler: SchedulerService, db: Database, bot: Bot) -> None:
        self.scheduler = scheduler
        self.db = db
        self.bot = bot
        self.reminders = ReminderRepository(db)
        self.bookings = BookingRepository(db)
        self.slots = SlotRepository(db)
        self.users = UserRepository(db)

    async def schedule_for_booking(self, booking_id: int, telegram_id: int) -> None:
        booking = await self.bookings.get_booking_by_id(booking_id)
        if not booking:
            return

        slot_dt = datetime.fromisoformat(f"{booking['date']}T{booking['time']}:00")
        run_at = slot_dt - timedelta(hours=24)
        now = datetime.now()
        if run_at <= now:
            return

        job_id = f"reminder:{booking_id}:{uuid.uuid4().hex[:8]}"
        self.scheduler.add_job(job_id=job_id, run_at=run_at, func=self._send_reminder_job, telegram_id=telegram_id, time=str(booking["time"]))
        await self.reminders.upsert(booking_id=booking_id, job_id=job_id, run_at=run_at)

    async def cancel_for_booking(self, booking_id: int) -> None:
        job_id = await self.reminders.delete_by_booking(booking_id)
        if job_id:
            self.scheduler.remove_job(job_id)

    async def restore_jobs_on_startup(self) -> None:
        now = datetime.now()
        all_rows = await self.reminders.get_all()
        for r in all_rows:
            booking_id = int(r["booking_id"])
            job_id = str(r["job_id"])
            run_at: datetime = r["run_at"]
            if run_at <= now:
                await self.reminders.delete_by_booking(booking_id)
                continue

            booking = await self.bookings.get_booking_by_id(booking_id)
            if not booking:
                await self.reminders.delete_by_booking(booking_id)
                continue

            # Need telegram_id to message user
            user_row = await self.db.fetchone(
                """
                SELECT u.telegram_id AS telegram_id
                FROM bookings b
                JOIN users u ON u.id = b.user_id
                WHERE b.id = ?;
                """,
                [booking_id],
            )
            if not user_row:
                await self.reminders.delete_by_booking(booking_id)
                continue

            telegram_id = int(user_row["telegram_id"])
            if not self.scheduler.has_job(job_id):
                self.scheduler.add_job(job_id=job_id, run_at=run_at, func=self._send_reminder_job, telegram_id=telegram_id, time=str(booking["time"]))

    async def _send_reminder_job(self, telegram_id: int, time: str) -> None:
        await self.bot.send_message(chat_id=telegram_id, text=REMINDER_TEXT_TEMPLATE.format(time=time))

