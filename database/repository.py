from __future__ import annotations

from datetime import datetime
from typing import Any, Optional

from database.database import Database


def _dt_to_str(dt: datetime) -> str:
    return dt.isoformat(timespec="seconds")


def _str_to_dt(value: str) -> datetime:
    return datetime.fromisoformat(value)


class UserRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_or_create(self, telegram_id: int) -> int:
        row = await self.db.fetchone("SELECT id FROM users WHERE telegram_id = ?;", [telegram_id])
        if row:
            return int(row["id"])
        await self.db.execute("INSERT INTO users(telegram_id) VALUES (?);", [telegram_id])
        row2 = await self.db.fetchone("SELECT id FROM users WHERE telegram_id = ?;", [telegram_id])
        if not row2:
            raise RuntimeError("Failed to create user")
        return int(row2["id"])

    async def update_profile(self, telegram_id: int, name: str, phone: str) -> None:
        await self.db.execute(
            "UPDATE users SET name = ?, phone = ? WHERE telegram_id = ?;",
            [name.strip(), phone.strip(), telegram_id],
        )

    async def get_by_telegram_id(self, telegram_id: int) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone("SELECT * FROM users WHERE telegram_id = ?;", [telegram_id])
        return dict(row) if row else None


class SlotRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def create_slots(self, date: str, times: list[str]) -> int:
        params = [(date, t, 1) for t in times]
        if not params:
            return 0
        await self.db.executemany(
            "INSERT OR IGNORE INTO slots(date, time, is_available) VALUES (?, ?, ?);",
            params,
        )
        row = await self.db.fetchone("SELECT COUNT(*) AS c FROM slots WHERE date = ?;", [date])
        return int(row["c"]) if row else 0

    async def set_day_availability(self, date: str, is_available: bool) -> None:
        await self.db.execute(
            "UPDATE slots SET is_available = ? WHERE date = ?;",
            [1 if is_available else 0, date],
        )

    async def delete_slot(self, slot_id: int) -> None:
        await self.db.execute("DELETE FROM slots WHERE id = ?;", [slot_id])

    async def get_available_dates(self, start_date: str, end_date: str) -> list[str]:
        rows = await self.db.fetchall(
            """
            SELECT DISTINCT date
            FROM slots
            WHERE is_available = 1 AND date BETWEEN ? AND ?
            ORDER BY date ASC;
            """,
            [start_date, end_date],
        )
        return [str(r["date"]) for r in rows]

    async def get_available_slots_by_date(self, date: str) -> list[dict[str, Any]]:
        rows = await self.db.fetchall(
            """
            SELECT id, date, time
            FROM slots
            WHERE date = ? AND is_available = 1
            ORDER BY time ASC;
            """,
            [date],
        )
        return [dict(r) for r in rows]

    async def get_slot(self, slot_id: int) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone("SELECT * FROM slots WHERE id = ?;", [slot_id])
        return dict(row) if row else None

    async def mark_unavailable(self, slot_id: int) -> None:
        await self.db.execute("UPDATE slots SET is_available = 0 WHERE id = ?;", [slot_id])

    async def mark_available(self, slot_id: int) -> None:
        await self.db.execute("UPDATE slots SET is_available = 1 WHERE id = ?;", [slot_id])

    async def get_slots_by_date(self, date: str) -> list[dict[str, Any]]:
        rows = await self.db.fetchall(
            "SELECT id, date, time, is_available FROM slots WHERE date = ? ORDER BY time ASC;",
            [date],
        )
        return [dict(r) for r in rows]


class BookingRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def get_user_booking(self, user_id: int) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone(
            """
            SELECT b.id AS booking_id, b.created_at, s.id AS slot_id, s.date, s.time
            FROM bookings b
            JOIN slots s ON s.id = b.slot_id
            WHERE b.user_id = ?;
            """,
            [user_id],
        )
        return dict(row) if row else None

    async def get_booking_by_id(self, booking_id: int) -> Optional[dict[str, Any]]:
        row = await self.db.fetchone(
            """
            SELECT b.id AS booking_id, b.user_id, b.slot_id, b.created_at, s.date, s.time
            FROM bookings b
            JOIN slots s ON s.id = b.slot_id
            WHERE b.id = ?;
            """,
            [booking_id],
        )
        return dict(row) if row else None

    async def create_booking(self, user_id: int, slot_id: int) -> int:
        created_at = _dt_to_str(datetime.now())
        await self.db.execute(
            "INSERT INTO bookings(user_id, slot_id, created_at) VALUES (?, ?, ?);",
            [user_id, slot_id, created_at],
        )
        row = await self.db.fetchone("SELECT id FROM bookings WHERE user_id = ?;", [user_id])
        if not row:
            raise RuntimeError("Failed to create booking")
        return int(row["id"])

    async def delete_booking(self, booking_id: int) -> None:
        await self.db.execute("DELETE FROM bookings WHERE id = ?;", [booking_id])

    async def find_booking_by_slot(self, slot_id: int) -> Optional[int]:
        row = await self.db.fetchone("SELECT id FROM bookings WHERE slot_id = ?;", [slot_id])
        return int(row["id"]) if row else None


class ReminderRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert(self, booking_id: int, job_id: str, run_at: datetime) -> None:
        await self.db.execute(
            """
            INSERT INTO reminders(booking_id, job_id, run_at)
            VALUES (?, ?, ?)
            ON CONFLICT(booking_id) DO UPDATE SET job_id = excluded.job_id, run_at = excluded.run_at;
            """,
            [booking_id, job_id, _dt_to_str(run_at)],
        )

    async def delete_by_booking(self, booking_id: int) -> Optional[str]:
        row = await self.db.fetchone("SELECT job_id FROM reminders WHERE booking_id = ?;", [booking_id])
        job_id = str(row["job_id"]) if row else None
        await self.db.execute("DELETE FROM reminders WHERE booking_id = ?;", [booking_id])
        return job_id

    async def get_all(self) -> list[dict[str, Any]]:
        rows = await self.db.fetchall("SELECT * FROM reminders ORDER BY run_at ASC;")
        out: list[dict[str, Any]] = []
        for r in rows:
            d = dict(r)
            d["run_at"] = _str_to_dt(str(d["run_at"]))
            out.append(d)
        return out

