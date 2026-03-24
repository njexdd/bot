from __future__ import annotations

import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from config import Settings, load_settings
from database.database import Database
from database.migrations import run_migrations
from services.scheduler_service import SchedulerService


logger = logging.getLogger(__name__)


class AppContext:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.bot = Bot(
            token=settings.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        self.dp = Dispatcher(storage=MemoryStorage())
        self.db = Database(db_path=settings.db_path)
        self.scheduler = SchedulerService(tz=settings.tz)

    async def startup(self) -> None:
        await self.db.connect()
        await run_migrations(self.db)
        await self.scheduler.start()

    async def shutdown(self) -> None:
        await self.scheduler.shutdown()
        await self.db.close()


def create_app() -> AppContext:
    settings = load_settings()
    return AppContext(settings)

