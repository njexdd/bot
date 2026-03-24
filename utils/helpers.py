from __future__ import annotations

import re
from datetime import date, datetime, timedelta


PHONE_RE = re.compile(r"^\+?\d{10,15}$")


def parse_phone(value: str) -> str | None:
    # Оставляем только цифры и возможный плюс в начале
    v = re.sub(r"[^\d+]", "", value or "")

    # Обработка популярных белорусских паттернов ввода
    if v.startswith("80") and len(v) == 11:
        v = "+375" + v[2:]
    elif v.startswith("375") and len(v) == 12:
        v = "+" + v
    elif not v.startswith("+") and len(v) == 9: 
        # Если ввели просто 9 цифр, например 291234567
        v = "+375" + v

    # Строгая проверка формата: +375 и 9 цифр после него
    match = re.match(r"^\+375(\d{2})(\d{3})(\d{2})(\d{2})$", v)
    if match:
        code, p1, p2, p3 = match.groups()
        return f"+375 ({code}) {p1}-{p2}-{p3}"
    
    return None


def today_iso() -> str:
    return date.today().isoformat()


def iso_in_days(days: int) -> str:
    return (date.today() + timedelta(days=days)).isoformat()


def now_dt() -> datetime:
    return datetime.now()

