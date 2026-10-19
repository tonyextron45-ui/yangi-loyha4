"""Yordamchi funksiyalar: obuna tekshiruvi, vaqt, bildirishnomalar.

TRAFIK TEJASH
─────────────
Obuna tekshiruvi — botning eng qimmat amali: har bir kanal uchun alohida
`get_chat_member` so'rovi Telegram API'ga ketadi. 3 kanal × 12 000 foydalanuvchi
× har harakat = millionlab so'rov.

Yechim (3 qatlam):
  1. `_pass_cache`  — foydalanuvchi to'liq o'tgan bo'lsa, TTL davomida umuman
                      tekshirilmaydi (0 ta API so'rovi).
  2. `_member_cache` — har bir (user, kanal) juftligi alohida keshlanadi, ya'ni
                      qayta tekshiruvda faqat YETISHMAYOTGAN kanal so'raladi.
  3. `chat_member` hodisasi — foydalanuvchi kanaldan chiqsa, kesh SHU ZAHOTI
                      bekor qilinadi. Ya'ni uzoq TTL ham xavfsiz.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timedelta, timezone
from typing import Any, Iterable

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramRetryAfter

from config import config
from database import queries as q
from utils.cache import TTLCache

log = logging.getLogger(__name__)

# O'zbekiston vaqti (UTC+5)
TZ = timezone(timedelta(hours=5))

_MEMBER_OK = {"member", "administrator", "creator"}

# Foydalanuvchi barcha kanallardan o'tgan → butunlay tekshirmaymiz.
_pass_cache: TTLCache = TTLCache(ttl=config.sub_cache_ttl, maxsize=100_000)
# (user_id, chat_id) → a'zo. Faqat ijobiy natija keshlanadi.
_member_cache: TTLCache = TTLCache(ttl=config.sub_cache_ttl, maxsize=200_000)


# ═══════════════════════════════════════════════════════
#                        VAQT
# ═══════════════════════════════════════════════════════

def now() -> datetime:
    return datetime.now(TZ)


def hhmm() -> str:
    return now().strftime("%H:%M")


def full_time() -> str:
    return now().strftime("%d.%m.%Y | %H:%M")


def fmt_date(unix: int | None) -> str:
    if not unix:
        return "—"
    return datetime.fromtimestamp(unix, TZ).strftime("%d.%m.%Y")


def minutes_left(until: int | None) -> int:
    if not until:
        return 0
    return max(0, (until - int(now().timestamp()) + 59) // 60)


def fmt_elapsed(seconds: float) -> str:
    total = int(seconds)
    mins, secs = divmod(total, 60)
    if mins:
        return f"{mins} daqiqa {secs} soniya"
    return f"{secs} soniya"


def fmt_left(seconds: float) -> str:
    """Qolgan vaqt: «12 kun 3 soat» ko'rinishida (premium/limit uchun)."""
    total = max(0, int(seconds))
    days, rem = divmod(total, 86400)
    hours, rem = divmod(rem, 3600)
    mins = rem // 60
    parts: list[str] = []
    if days:
        parts.append(f"{days} kun")
    if hours:
        parts.append(f"{hours} soat")
    if mins or not parts:
        parts.append(f"{mins} daqiqa")
    return " ".join(parts)


# ═══════════════════════════════════════════════════════
#                   OBUNA TEKSHIRUVI
# ═══════════════════════════════════════════════════════

def invalidate_subscription(user_id: int, chat_id: int | None = None) -> None:
    """Kesh bekor qilinadi — kanaldan chiqqanda darhol chaqiriladi."""
    _pass_cache.pop(user_id)
    if chat_id is not None:
        _member_cache.pop((user_id, chat_id))


def invalidate_all_subscriptions() -> None:
    """Kanallar ro'yxati o'zgardi — hamma keshni tashlaymiz."""
    _pass_cache.clear()
    _member_cache.clear()


async def _is_member(bot: Bot, chat_id: int, user_id: int) -> bool:
    key = (user_id, chat_id)
    if _member_cache.get(key):
        return True
    try:
        member = await bot.get_chat_member(chat_id, user_id)
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await _is_member(bot, chat_id, user_id)
    except TelegramAPIError as e:
        # Bot kanaldan chiqarilgan / kanal o'chirilgan — obunani majburlamaymiz,
        # aks holda admin xatosi tufayli hamma bloklanib qoladi.
        log.warning("get_chat_member(%s, %s) xato: %s", chat_id, user_id, e)
        return True
    ok = member.status in _MEMBER_OK
    if ok:
        _member_cache.set(key, True)
    return ok


async def missing_channels(bot: Bot, user_id: int) -> list[dict[str, Any]]:
    """Foydalanuvchi obuna bo'lmagan kanallar ro'yxati (bo'sh → hammasi joyida).

    Barcha kanallar PARALLEL tekshiriladi (asyncio.gather) — 3 ta kanal
    ketma-ket 3× kutish o'rniga bitta kutishda tugaydi.
    """
    mandatory = q.get_channels("mandatory")
    request = q.get_channels("request")
    if not mandatory and not request:
        return []

    # Zayavka kanallar uchun — bitta DB so'rovi (agar kerak bo'lsa).
    requested: set[int] = await q.join_request_chats(user_id) if request else set()

    async def check(chan: dict[str, Any], is_request: bool) -> dict[str, Any] | None:
        # Zayavka kanalda: so'rov yuborilgan bo'lsa — API'ga umuman bormaymiz.
        if is_request and chan["chat_id"] in requested:
            return None
        return None if await _is_member(bot, chan["chat_id"], user_id) else chan

    results = await asyncio.gather(
        *(check(c, False) for c in mandatory),
        *(check(c, True) for c in request),
    )
    return [c for c in results if c is not None]


async def subscription_gate(bot: Bot, user_id: int) -> list[dict[str, Any]]:
    """Yagona kirish nuqtasi: [] → ruxsat, aks holda yetishmayotgan kanallar.

    Kesh shu yerda yangilanadi, shuning uchun tekshiruv bir marta bajariladi
    (ikki marta API'ga bormaymiz).
    """
    if not q.sub_channels():
        return []
    if _pass_cache.get(user_id):
        return []
    # 💎 Premium obunachilar majburiy obunadan OZOD — panel umuman chiqmaydi.
    # (pass_cache'ga yozmaymiz: obuna tugashi bilan to'siq yana ishlashi kerak.)
    if await q.is_premium(user_id):
        return []
    missing = await missing_channels(bot, user_id)
    if not missing:
        _pass_cache.set(user_id, True)
    return missing


async def check_subscription(bot: Bot, user_id: int) -> bool:
    return not await subscription_gate(bot, user_id)


# ═══════════════════════════════════════════════════════
#                    BILDIRISHNOMA
# ═══════════════════════════════════════════════════════

async def notify_admins(bot: Bot, text: str, *, only_if_enabled: bool = True) -> None:
    """Barcha faol adminlarga parallel xabar (fon vazifasi — hech narsani bloklamaydi)."""
    if only_if_enabled and not q.notifications_on():
        return
    admins = [a["telegram_id"] for a in q.all_admins()]
    if not admins:
        return
    await asyncio.gather(*(safe_send(bot, tid, text) for tid in admins))


async def reward_referrer(bot: Bot, referred_id: int) -> None:
    """Taklif qilingan foydalanuvchi obunadan o'tgach — taklif qiluvchiga mukofot.

    Obuna to'sig'idan muvaffaqiyatli o'tgan har bir nuqtada chaqiriladi. Kutilayotgan
    referal bo'lmasa — darhol qaytadi (bitta tez, indeksli o'qish).
    """
    if not await q.has_pending_referral(referred_id):
        return
    claim = await q.claim_referral(referred_id)
    if claim is None:
        return
    if claim["reward"] > 0:
        from utils import texts

        balance = await q.add_balance(claim["referrer_id"], claim["reward"])
        await safe_send(
            bot, claim["referrer_id"], texts.referral_reward(claim["reward"], balance)
        )


async def safe_send(bot: Bot, chat_id: int, text: str, **kwargs: Any) -> bool:
    """Xato bermaydigan yuborish — bloklagan foydalanuvchi botni to'xtatmasin."""
    try:
        await bot.send_message(chat_id, text, **kwargs)
        return True
    except TelegramRetryAfter as e:
        await asyncio.sleep(e.retry_after)
        return await safe_send(bot, chat_id, text, **kwargs)
    except TelegramAPIError:
        return False


# ═══════════════════════════════════════════════════════
#                       BOSHQA
# ═══════════════════════════════════════════════════════

_background: set[asyncio.Task] = set()


def fire_and_forget(coro: Any) -> None:
    """Fon vazifasini xavfsiz ishga tushiradi.

    `asyncio.create_task` natijasiga havola saqlanmasa, vazifa tugagunicha
    axlat yig'uvchi uni yo'q qilib yuborishi mumkin (CPython'ning ma'lum
    xatosi) — shuning uchun havolani to'plamda ushlab turamiz.
    """
    task = asyncio.create_task(coro)
    _background.add(task)
    task.add_done_callback(_background.discard)


def chunked(items: list[Any], size: int) -> Iterable[list[Any]]:
    for i in range(0, len(items), size):
        yield items[i : i + size]


def parse_chat_ref(text: str) -> str | int | None:
    """«@kanal», «https://t.me/kanal», «-1001234567890» → aiogram uchun ref."""
    text = text.strip()
    if not text:
        return None
    if text.startswith("https://t.me/") or text.startswith("t.me/"):
        text = "@" + text.rsplit("/", 1)[-1]
    if text.startswith("@"):
        return text if len(text) > 1 else None
    try:
        return int(text)
    except ValueError:
        return None


def channel_link(chan: dict[str, Any]) -> str:
    """Obuna paneli tugmasi uchun URL."""
    if chan.get("invite_link"):
        return chan["invite_link"]
    if chan.get("username"):
        return f"https://t.me/{chan['username']}"
    return ""


def status_line(user: dict[str, Any]) -> str:
    """Foydalanuvchi holati — kartada real vaqtda ko'rinadi."""
    if user["is_banned"]:
        left = minutes_left(user["ban_until"])
        return f"⛔️ Bloklangan ({left} daqiqa qoldi)"
    return {
        "active": "🟢 Faol",
        "blocked": "🔴 Botni bloklagan",
        "left": "🚪 Botni tark etgan",
        "deleted": "💀 O'chirilgan akkaunt (nofaol)",
    }.get(user["status"], "🟢 Faol")
