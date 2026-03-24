from __future__ import annotations

import re
from datetime import date, datetime, timedelta


PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def parse_phone(value: str) -> str | None:
    v = (value or "").strip().replace(" ", "").replace("-", "").replace("(", "").replace(")", "")
    if v.startswith("8") and len(v) == 11:
        v = "+7" + v[1:]
    if not v.startswith("+") and v.isdigit():
        v = "+" + v
    return v if PHONE_RE.match(v) else None


def today_iso() -> str:
    return date.today().isoformat()


def iso_in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def now_dt() -> datetime:
    return datetime.now()

