from __future__ import annotations


def format_booking_html(*, date: str, time: str, name: str, phone: str, telegram_id: int) -> str:
    safe_name = (name or "").strip()
    safe_phone = (phone or "").strip()
    return (
        f"<b>Дата:</b> {date}\n"
        f"<b>Время:</b> {time}\n"
        f"<b>Имя:</b> {safe_name}\n"
        f"<b>Телефон:</b> {safe_phone}\n"
        f"<b>Telegram:</b> <a href=\"tg://user?id={telegram_id}\">{telegram_id}</a>"
    )

