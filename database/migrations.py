from __future__ import annotations

from database.database import Database


async def run_migrations(db: Database) -> None:
    # users
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            telegram_id INTEGER NOT NULL UNIQUE,
            name TEXT,
            phone TEXT
        );
        """
    )

    # slots
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS slots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            time TEXT NOT NULL,
            is_available INTEGER NOT NULL DEFAULT 1,
            UNIQUE(date, time)
        );
        """
    )

    # bookings
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS bookings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL UNIQUE,
            slot_id INTEGER NOT NULL UNIQUE,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE,
            FOREIGN KEY(slot_id) REFERENCES slots(id) ON DELETE CASCADE
        );
        """
    )

    # reminders
    await db.execute(
        """
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            booking_id INTEGER NOT NULL UNIQUE,
            job_id TEXT NOT NULL UNIQUE,
            run_at TEXT NOT NULL,
            FOREIGN KEY(booking_id) REFERENCES bookings(id) ON DELETE CASCADE
        );
        """
    )

    await db.execute("CREATE INDEX IF NOT EXISTS idx_slots_date_available ON slots(date, is_available);")
    await db.execute("CREATE INDEX IF NOT EXISTS idx_reminders_run_at ON reminders(run_at);")

