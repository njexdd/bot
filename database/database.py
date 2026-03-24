from __future__ import annotations

import asyncio
from typing import Any, Iterable, Optional

import aiosqlite


class Database:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._conn: Optional[aiosqlite.Connection] = None
        self._lock = asyncio.Lock()

    @property
    def conn(self) -> aiosqlite.Connection:
        if not self._conn:
            raise RuntimeError("Database is not connected")
        return self._conn

    async def connect(self) -> None:
        if self._conn:
            return
        self._conn = await aiosqlite.connect(self._db_path)
        self._conn.row_factory = aiosqlite.Row
        await self._conn.execute("PRAGMA foreign_keys = ON;")
        await self._conn.execute("PRAGMA journal_mode = WAL;")
        await self._conn.commit()

    async def close(self) -> None:
        if self._conn:
            await self._conn.close()
            self._conn = None

    async def execute(self, query: str, params: Iterable[Any] | None = None) -> None:
        async with self._lock:
            await self.conn.execute(query, params or [])
            await self.conn.commit()

    async def executemany(self, query: str, seq_of_params: list[Iterable[Any]]) -> None:
        async with self._lock:
            await self.conn.executemany(query, seq_of_params)
            await self.conn.commit()

    async def fetchone(self, query: str, params: Iterable[Any] | None = None) -> aiosqlite.Row | None:
        async with self._lock:
            cur = await self.conn.execute(query, params or [])
            row = await cur.fetchone()
            await cur.close()
            return row

    async def fetchall(self, query: str, params: Iterable[Any] | None = None) -> list[aiosqlite.Row]:
        async with self._lock:
            cur = await self.conn.execute(query, params or [])
            rows = await cur.fetchall()
            await cur.close()
            return rows

