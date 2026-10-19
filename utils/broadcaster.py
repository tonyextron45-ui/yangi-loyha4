"""Ommaviy xabar yuborish dvigateli.

ARXITEKTURA
───────────
  Producer  → keyset pagination bilan faol foydalanuvchilarni oqim sifatida
              o'qiydi (12 000 ID ni RAM'ga yig'maydi).
  Navbat    → cheklangan (maxsize), ya'ni xotira portlamaydi.
  Workers   → N ta parallel yuboruvchi (tarmoq kutishi ustma-ust tushadi).
  Limiter   → global token bucket: sekundiga aniq `rate` ta xabar.
              Bu `asyncio.sleep(0.05)` dan aniqroq — parallel worker'lar
              birgalikda ham limitdan oshmaydi.

`copy_message` ishlatiladi — barcha tur xabarlarni (stiker, dumaloq video,
forward, media) asl ko'rinishida saqlaydi va faylni qayta yuklamaydi.
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Awaitable, Callable

from aiogram import Bot
from aiogram.exceptions import (
    TelegramBadRequest,
    TelegramForbiddenError,
    TelegramRetryAfter,
)

from config import config
from database import queries as q

log = logging.getLogger(__name__)


class RateLimiter:
    """Global tezlik cheklovchisi — xabarlarni teng oraliqda tarqatadi."""

    __slots__ = ("_interval", "_next", "_lock")

    def __init__(self, rate: int) -> None:
        self._interval = 1.0 / rate
        self._next = 0.0
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        async with self._lock:
            now = time.monotonic()
            wait = self._next - now
            if wait > 0:
                await asyncio.sleep(wait)
                now = self._next
            self._next = max(now, self._next) + self._interval


def is_deleted_account(error: Exception) -> bool:
    """Telegram akkaunti O'CHIRILGANmi (shunchaki bloklaganmi emas)?

    Telegram o'chirilgan akkaunt uchun «user is deactivated», mavjud bo'lmagan
    chat uchun «chat not found» qaytaradi — ikkalasi ham nofaol (o'lik) akkaunt.
    Bot bloklangan bo'lsa esa «bot was blocked by the user» keladi.
    """
    msg = str(error).lower()
    return "deactivated" in msg or "chat not found" in msg or "user not found" in msg


@dataclass(slots=True)
class Progress:
    total: int = 0
    sent: int = 0
    failed: int = 0
    dead: list[int] = field(default_factory=list)
    deleted: list[int] = field(default_factory=list)

    @property
    def done(self) -> int:
        return self.sent + self.failed

    @property
    def percent(self) -> int:
        return int(self.done / self.total * 100) if self.total else 100


async def broadcast(
    bot: Bot,
    from_chat_id: int,
    message_id: int,
    on_progress: Callable[[Progress], Awaitable[None]] | None = None,
) -> tuple[Progress, float]:
    """Barcha faol foydalanuvchilarga yuboradi. → (natija, ketgan_vaqt)."""
    started = time.monotonic()
    progress = Progress(total=(await q.user_stats())["active"])

    limiter = RateLimiter(config.broadcast_rate)
    queue: asyncio.Queue[int | None] = asyncio.Queue(maxsize=config.broadcast_workers * 4)
    progress_lock = asyncio.Lock()

    async def send_one(uid: int) -> None:
        await limiter.acquire()
        try:
            await bot.copy_message(chat_id=uid, from_chat_id=from_chat_id, message_id=message_id)
            progress.sent += 1
        except TelegramRetryAfter as e:
            # Telegram «sekinlashtir» dedi — kutamiz va shu foydalanuvchini
            # qayta urinamiz (xabar yo'qolmaydi).
            log.warning("Flood limit: %s sek kutamiz", e.retry_after)
            await asyncio.sleep(e.retry_after)
            await send_one(uid)
        except TelegramForbiddenError as e:
            # Botni bloklagan yoki akkaunti o'chirilgan → statusini ajratamiz.
            progress.failed += 1
            (progress.deleted if is_deleted_account(e) else progress.dead).append(uid)
        except TelegramBadRequest as e:
            progress.failed += 1
            if is_deleted_account(e):
                progress.deleted.append(uid)
        except Exception as e:  # noqa: BLE001
            log.warning("Broadcast xatosi (%s): %s", uid, e)
            progress.failed += 1

    async def worker() -> None:
        while True:
            uid = await queue.get()
            if uid is None:
                queue.task_done()
                return
            try:
                await send_one(uid)
            finally:
                queue.task_done()

    async def reporter() -> None:
        """Hisobotni har 3 sekundda yangilaydi — har xabarda emas (trafik tejaladi)."""
        while progress.done < progress.total:
            await asyncio.sleep(3)
            if on_progress is not None:
                async with progress_lock:
                    await on_progress(progress)

    workers = [asyncio.create_task(worker()) for _ in range(config.broadcast_workers)]
    reporter_task = asyncio.create_task(reporter()) if on_progress else None

    try:
        async for chunk in q.iter_active_users(chunk=1000):
            for uid in chunk:
                await queue.put(uid)
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers)
    finally:
        if reporter_task is not None:
            reporter_task.cancel()
            await asyncio.gather(reporter_task, return_exceptions=True)

    # Yetib bormaganlar statusini BITTA batch bilan yangilaymiz.
    await _mark_dead(progress.dead, progress.deleted)

    return progress, time.monotonic() - started


async def _mark_dead(blocked: list[int], deleted: list[int]) -> None:
    """Yetib bormaganlarni belgilaymiz — keyingi broadcast ularga urinmaydi."""
    pairs = [("blocked", uid) for uid in blocked] + [("deleted", uid) for uid in deleted]
    if not pairs:
        return
    try:
        await q.bulk_set_status(pairs)
        log.info(
            "Broadcast: %d ta 'blocked', %d ta 'deleted' deb belgilandi",
            len(blocked), len(deleted),
        )
    except Exception:
        log.exception("Nofaol foydalanuvchilarni belgilashda xato")


# ═══════════════════════════════════════════════════════
#          🔍 NOFAOL AKKAUNTLARNI TEKSHIRISH
# ═══════════════════════════════════════════════════════

@dataclass(slots=True)
class ScanResult:
    total: int = 0
    checked: int = 0
    deleted: int = 0
    blocked: int = 0
    revived: int = 0


async def scan_inactive(
    bot: Bot,
    on_progress: Callable[[ScanResult], Awaitable[None]] | None = None,
) -> tuple[ScanResult, float]:
    """Har bir foydalanuvchini «tekshiradi» va statusini aniqlaydi.

    `send_chat_action` ishlatiladi — foydalanuvchiga HECH QANDAY xabar
    ko'rinmaydi, lekin Telegram akkaunt holatini aniq qaytaradi:
      • «user is deactivated» / «chat not found» → 💀 akkaunt o'chirilgan
      • «bot was blocked by the user»            → 🔴 botni bloklagan
      • xatosiz                                  → 🟢 faol
    """
    started = time.monotonic()
    result = ScanResult(total=await q.users_total())
    if not result.total:
        return result, 0.0

    limiter = RateLimiter(config.broadcast_rate)
    queue: asyncio.Queue[tuple[int, str] | None] = asyncio.Queue(
        maxsize=config.broadcast_workers * 4
    )
    changes: list[tuple[str, int]] = []

    async def check_one(uid: int, was: str) -> None:
        await limiter.acquire()
        try:
            await bot.send_chat_action(uid, "typing")
            status = "active"
        except TelegramRetryAfter as e:
            await asyncio.sleep(e.retry_after)
            await check_one(uid, was)
            return
        except (TelegramForbiddenError, TelegramBadRequest) as e:
            status = "deleted" if is_deleted_account(e) else "blocked"
        except Exception as e:  # noqa: BLE001
            # Noma'lum xato (tarmoq va h.k.) — statusga TEGMAYMIZ, aks holda
            # tirik foydalanuvchini xato bilan «o'lik» deb belgilab qo'yamiz.
            log.warning("Skaner xatosi (%s): %s", uid, e)
            result.checked += 1
            return

        result.checked += 1
        if status == "deleted":
            result.deleted += 1
        elif status == "blocked":
            result.blocked += 1
        elif was != "active":
            result.revived += 1

        if status != was:
            changes.append((status, uid))

    async def worker() -> None:
        while True:
            item = await queue.get()
            if item is None:
                queue.task_done()
                return
            try:
                await check_one(*item)
            finally:
                queue.task_done()

    async def reporter() -> None:
        while result.checked < result.total:
            await asyncio.sleep(3)
            if on_progress is not None:
                await on_progress(result)

    workers = [asyncio.create_task(worker()) for _ in range(config.broadcast_workers)]
    reporter_task = asyncio.create_task(reporter()) if on_progress else None

    try:
        async for chunk in q.iter_all_users(chunk=1000):
            for item in chunk:
                await queue.put(item)
        for _ in workers:
            await queue.put(None)
        await asyncio.gather(*workers)
    finally:
        if reporter_task is not None:
            reporter_task.cancel()
            await asyncio.gather(reporter_task, return_exceptions=True)

    await q.bulk_set_status(changes)
    return result, time.monotonic() - started
