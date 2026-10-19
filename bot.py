"""🎬 PREMIUM KINO BOT — ishga tushirish nuqtasi."""

from __future__ import annotations

import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiohttp import web
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import config
from database import queries as q
from database.db import db
from handlers.admin import router as admin_router
from handlers.user import router as user_router
from utils import texts
from utils.helpers import safe_send

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%H:%M:%S",
)
logging.getLogger("aiogram.event").setLevel(logging.WARNING)
log = logging.getLogger("kinobot")


# ═══════════════════════════════════════════════════════
#            HEALTH-SERVER (Render uchun majburiy)
# ═══════════════════════════════════════════════════════
# Render bepul «Web Service» PORT'ga ulanishni va HTTP javobni talab qiladi.
# Bu yengil server botni jonli ushlab turadi (UptimeRobot shu manzilni «ping»
# qiladi) — polling'ga xalaqit bermaydi.

async def _health(request: web.Request) -> web.Response:
    return web.Response(text="🎬 Tarjima Kinoman Bot — ishlayapti ✅")


async def start_health_server(port: int) -> web.AppRunner:
    app = web.Application()
    app.router.add_get("/", _health)
    app.router.add_get("/health", _health)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()
    log.info("🌐 Health-server tayyor: 0.0.0.0:%d", port)
    return runner


# ═══════════════════════════════════════════════════════
#                  FON VAZIFALARI
# ═══════════════════════════════════════════════════════

async def unban_expired(bot: Bot) -> None:
    """Har daqiqada: muddati tugagan bloklarni ochadi (TZ §8.3.3)."""
    ids = await q.pop_expired_bans()
    if not ids:
        return
    log.info("Blok muddati tugadi: %d ta foydalanuvchi", len(ids))
    await asyncio.gather(*(safe_send(bot, tid, texts.BAN_EXPIRED) for tid in ids))


async def expire_premium(bot: Bot) -> None:
    """Muddati tugagan premium obunalarni bekor qiladi + foydalanuvchiga xabar."""
    ids = await q.pop_expired_premium()
    if not ids:
        return
    log.info("Premium muddati tugadi: %d ta foydalanuvchi", len(ids))
    await asyncio.gather(
        *(safe_send(bot, tid, texts.premium_expired_notice()) for tid in ids)
    )


def setup_scheduler(bot: Bot) -> AsyncIOScheduler:
    sched = AsyncIOScheduler(timezone="Asia/Tashkent")

    # Blok muddatini kuzatish.
    sched.add_job(unban_expired, "interval", minutes=1, args=(bot,), id="unban")

    # Premium obuna muddatini kuzatish.
    sched.add_job(expire_premium, "interval", minutes=5, args=(bot,), id="premium")

    # Yozuv buferlarini diskka tashlash (ko'rishlar, last_seen).
    sched.add_job(q.flush_buffers, "interval", seconds=30, id="flush")

    # Baza texnik xizmati (lokalda foydali, remote'da zararsiz).
    sched.add_job(db.optimize, "interval", hours=6, id="optimize")

    sched.start()
    return sched


# ═══════════════════════════════════════════════════════
#                    HAYOT SIKLI
# ═══════════════════════════════════════════════════════

async def on_startup(bot: Bot) -> None:
    await db.connect()
    await q.warmup()                              # keshlarni to'ldirish
    await q.ensure_main_admin(config.main_admin_id)

    me = await bot.me()                           # natija keshlanadi
    log.info("🎬 @%s ishga tushdi (id=%s)", me.username, me.id)
    log.info(
        "📊 Adminlar: %d | Kanallar: %s | Keyingi kod: %d",
        len(q.all_admins()),
        q.channel_stats(),
        int(q.get_setting("code_counter", "9999")) + 1,
    )

    storage = "Turso (bulut, doimiy)" if config.turso_url else "Lokal SQLite fayl"
    await safe_send(
        bot,
        config.main_admin_id,
        f"🚀 <b>Bot ishga tushdi!</b>\n\n🤖 @{me.username}\n💾 Baza: {storage}",
    )


async def on_shutdown(bot: Bot) -> None:
    log.info("To'xtatilmoqda... buferlar saqlanmoqda")
    await q.flush_buffers()   # xotiradagi ko'rishlar yo'qolmasin
    await db.close()
    log.info("👋 Bot to'xtadi")


async def main() -> None:
    bot = Bot(
        token=config.bot_token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML,
            link_preview_is_disabled=True,
        ),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # TARTIB MUHIM: admin routerlari birinchi.
    # Aks holda foydalanuvchi qismidagi «raqam emas» to'sig'i admin
    # tugmalarini va FSM jarayonlarini ushlab qolardi.
    dp.include_router(admin_router)
    dp.include_router(user_router)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    # Health-server'ni polling'dan OLDIN ishga tushiramiz — Render darhol
    # ochiq portni ko'rsin (aks holda «deploy failed» deb hisoblaydi).
    health_runner = await start_health_server(config.port)
    scheduler = setup_scheduler(bot)

    try:
        await bot.delete_webhook(drop_pending_updates=True)
        # `chat_member` ni ham so'raymiz — obuna keshini real vaqtda bekor
        # qilish uchun (utils/helpers.py ga qarang).
        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types(),
        )
    finally:
        scheduler.shutdown(wait=False)
        await health_runner.cleanup()
        await bot.session.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    else:
        with __import__("contextlib").suppress(ImportError):
            import uvloop

            uvloop.install()  # Linux'da ~2× tezroq event loop

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        log.info("👋 Xayr!")
