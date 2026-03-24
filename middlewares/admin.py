from __future__ import annotations

from typing import Any, Awaitable, Callable, Dict, Union

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject


class AdminMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: Union[Message, CallbackQuery, TelegramObject],
        data: Dict[str, Any],
    ) -> Any:
        from_user = data.get("event_from_user")
        if not from_user:
            return await handler(event, data)

        settings = None
        try:
            settings = data["dispatcher"]["app"].settings  # type: ignore[index]
        except Exception:
            settings = None

        if not settings:
            return await handler(event, data)

        user_id = int(from_user.id)

        if isinstance(event, CallbackQuery):
            cd = event.data or ""
            is_admin_area = cd.startswith("adm:") or cd == "menu:admin"
            if is_admin_area and user_id != int(settings.admin_id):
                await event.answer("Нет доступа.", show_alert=True)
                return

        return await handler(event, data)

