from __future__ import annotations

import asyncio
import logging

from aiogram import Router

from handlers import admin, booking, my_booking, portfolio, prices, start
from loader import create_app
from middlewares.admin import AdminMiddleware
from services.reminder_service import ReminderService


def setup_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )


def include_routers(root: Router) -> None:
    root.include_router(start.router)
    root.include_router(prices.router)
    root.include_router(portfolio.router)
    root.include_router(booking.router)
    root.include_router(my_booking.router)
    root.include_router(admin.router)


async def main() -> None:
    setup_logging()

    app = create_app()

    app.dp["app"] = app

    app.dp.callback_query.middleware(AdminMiddleware())
    app.dp.message.middleware(AdminMiddleware())

    include_routers(app.dp)

    await app.startup()

    reminder_service = ReminderService(app.scheduler, app.db, app.bot)
    await reminder_service.restore_jobs_on_startup()

    try:
        await app.dp.start_polling(app.bot, allowed_updates=app.dp.resolve_used_update_types())
    finally:
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

