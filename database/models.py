from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass(slots=True)
class User:
    id: int
    telegram_id: int
    name: Optional[str]
    phone: Optional[str]


@dataclass(slots=True)
class Slot:
    id: int
    date: str  # YYYY-MM-DD
    time: str  # HH:MM
    is_available: bool


@dataclass(slots=True)
class Booking:
    id: int
    user_id: int
    slot_id: int
    created_at: datetime


@dataclass(slots=True)
class Reminder:
    id: int
    booking_id: int
    job_id: str
    run_at: datetime

