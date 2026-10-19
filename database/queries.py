"""Barcha CRUD funksiyalar + kesh qatlami + yozuv buferlari.

TEZLIK STRATEGIYASI
───────────────────
1. Issiq ma'lumot xotirada:  adminlar, kanallar, sozlamalar — DB'ga umuman
   bormaydi (o'zgarganda kesh darhol bekor qilinadi).
2. Yozuv buferlari:  ko'rishlar va last_seen har harakatda diskka yozilmaydi,
   xotirada yig'ilib, davriy ravishda BITTA tranzaksiyada tashlanadi.
   12 000 foydalanuvchi → sekundiga yuzlab yozuv o'rniga 30 sekundda 1 ta.
3. Kontent LRU keshi:  ommabop kodlar diskka tegmasdan qaytadi.
"""

from __future__ import annotations

import logging
import time
from typing import Any, AsyncIterator, Iterable, Literal

from config import config
from database.db import Row, db
from utils.cache import LRUCache, TTLCache

log = logging.getLogger(__name__)

# ═══════════════════ KESHLAR ═══════════════════

_settings: dict[str, str] = {}                   # to'liq yuklanadi, doim yangi
_admins: dict[int, dict[str, Any]] = {}          # telegram_id -> admin
_channels: dict[str, list[dict[str, Any]]] = {}  # ctype -> kanallar
_content_cache: LRUCache = LRUCache(maxsize=1024)
_episodes_cache: LRUCache = LRUCache(maxsize=256)
_user_cache: TTLCache = TTLCache(ttl=300, maxsize=50_000)
_stats_cache: TTLCache = TTLCache(ttl=5, maxsize=8)

# ═══════════════════ YOZUV BUFERLARI ═══════════════════

_views_buf: dict[int, int] = {}   # code -> qo'shiladigan ko'rishlar
_seen_buf: dict[int, int] = {}    # telegram_id -> last_seen (unix)


def _now() -> int:
    return int(time.time())


def _row(row: Row | None) -> dict[str, Any] | None:
    return dict(row) if row is not None else None


# ═══════════════════════════════════════════════════════
#                      SOZLAMALAR
# ═══════════════════════════════════════════════════════

async def load_settings() -> None:
    """Startda bir marta — keyin barcha o'qishlar xotiradan."""
    _settings.clear()
    for row in await db.fetchall("SELECT key, value FROM settings"):
        _settings[row["key"]] = row["value"]


def get_setting(key: str, default: str = "") -> str:
    return _settings.get(key, default)


async def set_setting(key: str, value: str) -> None:
    await db.execute(
        "INSERT INTO settings(key, value) VALUES(?, ?) "
        "ON CONFLICT(key) DO UPDATE SET value = excluded.value",
        (key, value),
    )
    _settings[key] = value


def notifications_on() -> bool:
    return _settings.get("notifications", "off") == "on"


async def toggle_notifications() -> bool:
    new = "off" if notifications_on() else "on"
    await set_setting("notifications", new)
    return new == "on"


# ═══════════════════════════════════════════════════════
#                  KOD GENERATSIYASI
# ═══════════════════════════════════════════════════════

async def next_code() -> int:
    """Atomik +1. Bir vaqtda 2 admin qo'shsa ham kodlar to'qnashmaydi.

    Yozuvchi ulanish yagona va Lock bilan himoyalangani uchun bu amal
    tabiiy ravishda serializatsiya qilinadi.
    """
    row = await db.returning(
        "UPDATE settings SET value = CAST(CAST(value AS INTEGER) + 1 AS TEXT) "
        "WHERE key = 'code_counter' RETURNING CAST(value AS INTEGER)"
    )
    code = int(row[0])
    _settings["code_counter"] = str(code)
    return code


# ═══════════════════════════════════════════════════════
#                   FOYDALANUVCHILAR
# ═══════════════════════════════════════════════════════

async def get_user(tid: int) -> dict[str, Any] | None:
    cached = _user_cache.get(tid)
    if cached is not None:
        return cached
    user = _row(await db.fetchone("SELECT * FROM users WHERE telegram_id = ?", (tid,)))
    if user is not None:
        _user_cache.set(tid, user)
    return user


def invalidate_user(tid: int) -> None:
    _user_cache.pop(tid)


async def register_user(tid: int, username: str | None, full_name: str) -> bool:
    """Foydalanuvchini yozadi. True → yangi (bildirishnoma yuboriladi)."""
    existing = await get_user(tid)
    if existing is not None:
        # Qayta /start bosgan — profil yangilanadi, 'left/blocked' → 'active'.
        if (
            existing["status"] != "active"
            or existing["username"] != username
            or existing["full_name"] != full_name
        ):
            await db.execute(
                "UPDATE users SET username = ?, full_name = ?, status = 'active', "
                "last_seen = ? WHERE telegram_id = ?",
                (username, full_name, _now(), tid),
            )
            invalidate_user(tid)
            _stats_cache.clear()
        return False

    await db.execute(
        "INSERT OR IGNORE INTO users(telegram_id, username, full_name) VALUES(?, ?, ?)",
        (tid, username, full_name),
    )
    invalidate_user(tid)
    _stats_cache.clear()
    return True


def touch_user(tid: int) -> None:
    """last_seen — buferga. Diskka davriy tashlanadi (flush_buffers)."""
    _seen_buf[tid] = _now()


async def set_status(tid: int, status: Literal["active", "blocked", "left", "deleted"]) -> None:
    await db.execute("UPDATE users SET status = ? WHERE telegram_id = ?", (status, tid))
    invalidate_user(tid)
    _stats_cache.clear()


async def ban_user(tid: int, minutes: int) -> int:
    until = _now() + minutes * 60
    await db.execute(
        "UPDATE users SET is_banned = 1, ban_until = ? WHERE telegram_id = ?", (until, tid)
    )
    invalidate_user(tid)
    _stats_cache.clear()
    return until


async def unban_user(tid: int) -> None:
    await db.execute(
        "UPDATE users SET is_banned = 0, ban_until = NULL WHERE telegram_id = ?", (tid,)
    )
    invalidate_user(tid)
    _stats_cache.clear()


async def pop_expired_bans() -> list[int]:
    """Muddati tugagan bloklarni ochadi va ularning ID larini qaytaradi."""
    rows = await db.fetchall(
        "SELECT telegram_id FROM users WHERE is_banned = 1 AND ban_until IS NOT NULL "
        "AND ban_until <= ?",
        (_now(),),
    )
    if not rows:
        return []
    ids = [r["telegram_id"] for r in rows]
    await db.execute(
        "UPDATE users SET is_banned = 0, ban_until = NULL "
        "WHERE is_banned = 1 AND ban_until IS NOT NULL AND ban_until <= ?",
        (_now(),),
    )
    for tid in ids:
        invalidate_user(tid)
    _stats_cache.clear()
    return ids


async def user_stats() -> dict[str, int]:
    """Statistika. `deleted` — Telegram akkaunti o'chirilgan (nofaol) foydalanuvchilar,
    `inactive` — botga xabar yetib bormaydigan HAMMA holat (bloklagan + tark etgan +
    o'chirilgan)."""
    cached = _stats_cache.get("users")
    if cached is not None:
        return cached
    row = await db.fetchone(
        """
        SELECT COUNT(*)                            AS total,
               SUM(status = 'active')              AS active,
               SUM(status = 'blocked')             AS blocked,
               SUM(status = 'left')                AS gone,
               SUM(status = 'deleted')             AS deleted,
               SUM(status <> 'active')             AS inactive,
               SUM(is_banned = 1)                  AS banned,
               SUM(joined_at >= ?)                 AS today,
               SUM(joined_at >= ?)                 AS week,
               SUM(joined_at >= ?)                 AS month
        FROM users
        """,
        (_now() - 86400, _now() - 7 * 86400, _now() - 30 * 86400),
    )
    stats = {k: (row[k] or 0) for k in row.keys()}
    _stats_cache.set("users", stats)
    return stats


async def users_page(offset: int, limit: int) -> list[int]:
    rows = await db.fetchall(
        "SELECT telegram_id FROM users ORDER BY id LIMIT ? OFFSET ?", (limit, offset)
    )
    return [r["telegram_id"] for r in rows]


async def users_total() -> int:
    return await db.fetchval("SELECT COUNT(*) FROM users", default=0)


async def iter_active_users(chunk: int = 1000) -> AsyncIterator[list[int]]:
    """Broadcast uchun keyset pagination — OFFSET'dan tez, RAM'ni yemaydi."""
    last_id = 0
    while True:
        rows = await db.fetchall(
            "SELECT id, telegram_id FROM users WHERE status = 'active' AND id > ? "
            "ORDER BY id LIMIT ?",
            (last_id, chunk),
        )
        if not rows:
            return
        last_id = rows[-1]["id"]
        yield [r["telegram_id"] for r in rows]


async def iter_all_users(chunk: int = 1000) -> AsyncIterator[list[tuple[int, str]]]:
    """Nofaol akkauntlarni tekshirish uchun — HAMMA foydalanuvchi: (telegram_id, status).

    Statusi ham beriladi, chunki skaner faqat O'ZGARGANLARINI yozadi va
    «qayta faollashgan» sonini shundan hisoblaydi.
    """
    last_id = 0
    while True:
        rows = await db.fetchall(
            "SELECT id, telegram_id, status FROM users WHERE id > ? ORDER BY id LIMIT ?",
            (last_id, chunk),
        )
        if not rows:
            return
        last_id = rows[-1]["id"]
        yield [(r["telegram_id"], r["status"]) for r in rows]


async def bulk_set_status(pairs: list[tuple[str, int]]) -> None:
    """[(status, telegram_id), ...] — statuslarni ommaviy yangilaydi (skaner/broadcast).

    500 tadan bo'lib yuboriladi: bitta ulkan batch remote (Turso) so'rov
    hajmi chegarasiga urilishi mumkin.
    """
    if not pairs:
        return
    for i in range(0, len(pairs), 500):
        await db.executemany(
            "UPDATE users SET status = ? WHERE telegram_id = ? AND status <> ?",
            [(status, tid, status) for status, tid in pairs[i : i + 500]],
        )
    for _, tid in pairs:
        invalidate_user(tid)
    _stats_cache.clear()


# ═══════════════════════════════════════════════════════
#                       ADMINLAR
# ═══════════════════════════════════════════════════════

async def load_admins() -> None:
    _admins.clear()
    for row in await db.fetchall("SELECT * FROM admins WHERE is_active = 1"):
        _admins[row["telegram_id"]] = dict(row)


def get_admin(tid: int) -> dict[str, Any] | None:
    """Xotiradan — har bir update'da chaqiriladi, DB'ga bormaydi."""
    return _admins.get(tid)


def is_admin(tid: int) -> bool:
    return tid in _admins


def is_main_admin(tid: int) -> bool:
    return tid == config.main_admin_id


def all_admins() -> list[dict[str, Any]]:
    return sorted(_admins.values(), key=lambda a: (a["role"] != "main", a["added_at"]))


def has_perm(tid: int, perm: Literal["content", "channels", "admins"]) -> bool:
    if is_main_admin(tid):
        return True
    admin = _admins.get(tid)
    return bool(admin and admin[f"can_{perm}"])


async def ensure_main_admin(tid: int) -> None:
    """Asosiy admin — barcha huquqlar bilan, har startda kafolatlanadi."""
    await db.execute(
        """
        INSERT INTO admins(telegram_id, role, can_content, can_channels, can_admins)
        VALUES(?, 'main', 1, 1, 1)
        ON CONFLICT(telegram_id) DO UPDATE SET
            role = 'main', can_content = 1, can_channels = 1, can_admins = 1, is_active = 1
        """,
        (tid,),
    )
    await load_admins()


async def add_admin(tid: int) -> bool:
    if tid in _admins:
        return False
    await db.execute(
        "INSERT INTO admins(telegram_id, role) VALUES(?, 'helper') "
        "ON CONFLICT(telegram_id) DO UPDATE SET is_active = 1",
        (tid,),
    )
    await load_admins()
    return True


async def remove_admin(tid: int) -> bool:
    if tid == config.main_admin_id:
        return False
    await db.execute("DELETE FROM admins WHERE telegram_id = ?", (tid,))
    await load_admins()
    return True


async def toggle_perm(tid: int, perm: Literal["content", "channels", "admins"]) -> bool:
    """Huquqni teskarisiga o'zgartiradi → yangi holatni qaytaradi."""
    col = f"can_{perm}"
    row = await db.returning(
        f"UPDATE admins SET {col} = 1 - {col} WHERE telegram_id = ? RETURNING {col}",
        (tid,),
    )
    await load_admins()
    return bool(row[0]) if row else False


# ═══════════════════════════════════════════════════════
#                        KONTENT
# ═══════════════════════════════════════════════════════

async def create_content(
    code: int,
    ctype: Literal["movie", "series"],
    *,
    title: str,
    caption: str,
    trailer_file_id: str,
    trailer_type: str,
    trailer_msg_id: int | None,
    file_id: str | None = None,
    base_msg_id: int | None = None,
    is_paid: bool = False,
    price: int = 0,
    added_by: int,
) -> None:
    await db.execute(
        "INSERT INTO content(code, ctype, title, caption, file_id, base_msg_id, "
        "trailer_file_id, trailer_type, trailer_msg_id, is_paid, price, added_by) "
        "VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (code, ctype, title, caption, file_id, base_msg_id,
         trailer_file_id, trailer_type, trailer_msg_id, int(is_paid), price, added_by),
    )
    _content_cache.pop(code)
    _stats_cache.clear()


async def update_content_caption(code: int, caption: str) -> bool:
    """Tavsifni (body) o'zgartiradi — tahrirlash uchun. → topildi_mi."""
    content = await get_content(code, only_live=True)
    if content is None:
        return False
    await db.execute("UPDATE content SET caption = ? WHERE code = ?", (caption, code))
    _content_cache.pop(code)
    return True


async def get_content(code: int, *, only_live: bool = True) -> dict[str, Any] | None:
    """Issiq kodlar LRU keshdan qaytadi — diskka tegmaydi."""
    cached = _content_cache.get(code)
    if cached is None:
        cached = _row(await db.fetchone("SELECT * FROM content WHERE code = ?", (code,)))
        if cached is None:
            return None
        _content_cache.set(code, cached)
    if only_live and cached["is_deleted"]:
        return None
    return cached


async def delete_content(code: int) -> dict[str, Any] | None:
    """Soft delete — qator qolaveradi, kod abadiy band."""
    content = await get_content(code, only_live=True)
    if content is None:
        return None
    await db.execute("UPDATE content SET is_deleted = 1 WHERE code = ?", (code,))
    _content_cache.pop(code)
    _episodes_cache.pop(code)
    _stats_cache.clear()
    return content


def bump_views(code: int) -> None:
    """Ko'rishlarni buferga qo'shadi — flush_buffers() diskka tashlaydi."""
    _views_buf[code] = _views_buf.get(code, 0) + 1
    cached = _content_cache.get(code)
    if cached is not None:
        # Kartada darhol yangi raqam ko'rinsin (bufer hali tashlanmagan bo'lsa ham).
        cached["views"] += 1


async def add_episode(code: int, ep: int, file_id: str, base_msg_id: int | None) -> None:
    await db.execute(
        "INSERT INTO episodes(series_code, ep_number, file_id, base_msg_id) "
        "VALUES(?, ?, ?, ?) ON CONFLICT(series_code, ep_number) DO UPDATE SET "
        "file_id = excluded.file_id, base_msg_id = excluded.base_msg_id",
        (code, ep, file_id, base_msg_id),
    )
    _episodes_cache.pop(code)
    _stats_cache.clear()


async def delete_episode(code: int, ep_number: int) -> tuple[bool, int | None]:
    """Bitta qismni o'chiradi. → (topildi_mi, baza_xabar_id).

    Qism raqamlari qayta tartiblanmaydi — mavjudlari o'z raqamida qoladi
    (masalan 3-qism o'chsa: 1, 2, 4, 5). series_kb bo'shliqni to'g'ri chizadi.
    """
    row = await db.returning(
        "DELETE FROM episodes WHERE series_code = ? AND ep_number = ? "
        "RETURNING base_msg_id",
        (code, ep_number),
    )
    if row is None:
        return False, None
    _episodes_cache.pop(code)
    _stats_cache.clear()
    return True, row[0]


async def get_episodes(code: int) -> list[dict[str, Any]]:
    cached = _episodes_cache.get(code)
    if cached is not None:
        return cached
    rows = await db.fetchall(
        "SELECT ep_number, file_id, base_msg_id FROM episodes "
        "WHERE series_code = ? ORDER BY ep_number",
        (code,),
    )
    eps = [dict(r) for r in rows]
    _episodes_cache.set(code, eps)
    return eps


async def episode_count(code: int) -> int:
    return len(await get_episodes(code))


async def last_episode_number(code: int) -> int:
    return await db.fetchval(
        "SELECT COALESCE(MAX(ep_number), 0) FROM episodes WHERE series_code = ?",
        (code,),
        default=0,
    )


async def content_stats() -> dict[str, int]:
    cached = _stats_cache.get("content")
    if cached is not None:
        return cached
    row = await db.fetchone(
        """
        SELECT SUM(ctype = 'movie'  AND is_deleted = 0) AS movies,
               SUM(ctype = 'series' AND is_deleted = 0) AS series,
               SUM(is_deleted = 1)                      AS deleted,
               COALESCE(SUM(views), 0)                  AS views
        FROM content
        """
    )
    eps = await db.fetchval(
        "SELECT COUNT(*) FROM episodes e JOIN content c ON c.code = e.series_code "
        "WHERE c.is_deleted = 0",
        default=0,
    )
    stats = {
        "movies": row["movies"] or 0,
        "series": row["series"] or 0,
        "deleted": row["deleted"] or 0,
        "views": (row["views"] or 0) + sum(_views_buf.values()),
        "episodes": eps,
    }
    _stats_cache.set("content", stats)
    return stats


async def top_content(limit: int = 10) -> list[dict[str, Any]]:
    rows = await db.fetchall(
        "SELECT code, ctype, title, caption, views FROM content WHERE is_deleted = 0 "
        "ORDER BY views DESC LIMIT ?",
        (limit,),
    )
    return [dict(r) for r in rows]


# ═══════════════════════════════════════════════════════
#                        BALANS
# ═══════════════════════════════════════════════════════

async def get_balance(tid: int) -> int:
    user = await get_user(tid)
    return int(user["balance"]) if user else 0


async def add_balance(tid: int, amount: int) -> int:
    """Balansni oshiradi → yangi balansni qaytaradi."""
    await db.execute(
        "UPDATE users SET balance = balance + ? WHERE telegram_id = ?", (amount, tid)
    )
    invalidate_user(tid)
    return await get_balance(tid)


async def deduct_balance(tid: int, amount: int) -> bool:
    """Balansdan yechadi (yetarli bo'lsa). Atomik — ikki marta yechilmaydi."""
    affected = await db.execute(
        "UPDATE users SET balance = balance - ? WHERE telegram_id = ? AND balance >= ?",
        (amount, tid, amount),
    )
    if affected:
        invalidate_user(tid)
        return True
    return False


# ═══════════════════════════════════════════════════════
#                   PREMIUM OBUNA
# ═══════════════════════════════════════════════════════

TARIFF_DAYS: dict[str, int] = {"1m": 30, "3m": 90, "6m": 180, "1y": 365}
TARIFF_LABEL: dict[str, str] = {"1m": "1 oy", "3m": "3 oy", "6m": "6 oy", "1y": "1 yil"}


def premium_active(user: dict[str, Any] | None) -> bool:
    if not user:
        return False
    until = user.get("premium_until")
    return bool(until and until > _now())


async def is_premium(tid: int) -> bool:
    return premium_active(await get_user(tid))


def tariff_prices() -> dict[str, int]:
    return {t: int(get_setting(f"tariff_{t}", "0") or 0) for t in TARIFF_DAYS}


def tariff_price(tariff: str) -> int:
    return int(get_setting(f"tariff_{tariff}", "0") or 0)


async def grant_premium(tid: int, tariff: str) -> int:
    """Premium beradi (mavjud bo'lsa uzaytiradi). → tugash vaqti (unix)."""
    now = _now()
    days = TARIFF_DAYS.get(tariff, 30)
    user = await get_user(tid)
    base = now
    if user and user.get("premium_until") and user["premium_until"] > now:
        base = user["premium_until"]
    until = base + days * 86400
    await db.execute(
        "UPDATE users SET premium_until = ?, premium_tariff = ?, premium_started = ? "
        "WHERE telegram_id = ?",
        (until, tariff, now, tid),
    )
    invalidate_user(tid)
    return until


async def cancel_premium(tid: int) -> None:
    await db.execute(
        "UPDATE users SET premium_until = NULL, premium_tariff = NULL, "
        "premium_started = NULL WHERE telegram_id = ?",
        (tid,),
    )
    invalidate_user(tid)


async def pop_expired_premium() -> list[int]:
    """Muddati tugagan premiumlarni tozalaydi va ID larni qaytaradi."""
    now = _now()
    rows = await db.fetchall(
        "SELECT telegram_id FROM users WHERE premium_until IS NOT NULL AND premium_until <= ?",
        (now,),
    )
    if not rows:
        return []
    ids = [r["telegram_id"] for r in rows]
    await db.execute(
        "UPDATE users SET premium_until = NULL, premium_tariff = NULL, "
        "premium_started = NULL WHERE premium_until IS NOT NULL AND premium_until <= ?",
        (now,),
    )
    for tid in ids:
        invalidate_user(tid)
    return ids


async def premium_users() -> list[int]:
    """Faol premium obunachilar (tugash vaqti yaqinlariga tartiblangan)."""
    now = _now()
    rows = await db.fetchall(
        "SELECT telegram_id FROM users WHERE premium_until IS NOT NULL "
        "AND premium_until > ? ORDER BY premium_until",
        (now,),
    )
    return [r["telegram_id"] for r in rows]


# ═══════════════════════════════════════════════════════
#                   SOTIB OLISHLAR
# ═══════════════════════════════════════════════════════

async def has_purchased(tid: int, code: int) -> bool:
    row = await db.fetchone(
        "SELECT 1 FROM purchases WHERE user_id = ? AND code = ?", (tid, code)
    )
    return row is not None


async def add_purchase(tid: int, code: int, price: int) -> bool:
    """Sotib olishni yozadi. → True faqat YANGI yozuv bo'lsa (takrorlanmasa).

    Bu «qulf» vazifasini bajaradi: tugma ikki marta tez bosilsa ham, faqat
    bitta chaqiruv True oladi — shu tufayli balansdan ikki marta yechilmaydi.
    """
    row = await db.returning(
        "INSERT OR IGNORE INTO purchases(user_id, code, price) VALUES(?, ?, ?) "
        "RETURNING id",
        (tid, code, price),
    )
    return row is not None


async def remove_purchase(tid: int, code: int) -> None:
    """Sotib olishni bekor qiladi (balansdan yechish muvaffaqiyatsiz bo'lsa)."""
    await db.execute("DELETE FROM purchases WHERE user_id = ? AND code = ?", (tid, code))


async def purchases_count(tid: int) -> int:
    return await db.fetchval(
        "SELECT COUNT(*) FROM purchases WHERE user_id = ?", (tid,), default=0
    )


async def has_access(tid: int, content: dict[str, Any]) -> bool:
    """Pullik kontentga kirish huquqi: bepul / premium / sotib olingan."""
    if not content.get("is_paid"):
        return True
    if await is_premium(tid):
        return True
    return await has_purchased(tid, content["code"])


# ═══════════════════════════════════════════════════════
#                   TO'LOV KARTALARI
# ═══════════════════════════════════════════════════════

async def get_cards() -> list[dict[str, Any]]:
    rows = await db.fetchall("SELECT * FROM cards ORDER BY id")
    return [dict(r) for r in rows]


async def get_card(cid: int) -> dict[str, Any] | None:
    return _row(await db.fetchone("SELECT * FROM cards WHERE id = ?", (cid,)))


async def add_card(number: str, holder: str) -> None:
    await db.execute("INSERT INTO cards(number, holder) VALUES(?, ?)", (number, holder))


async def update_card(cid: int, number: str, holder: str) -> None:
    await db.execute(
        "UPDATE cards SET number = ?, holder = ? WHERE id = ?", (number, holder, cid)
    )


async def delete_card(cid: int) -> bool:
    return bool(await db.execute("DELETE FROM cards WHERE id = ?", (cid,)))


# ═══════════════════════════════════════════════════════
#              BALANS TO'LDIRISH SO'ROVLARI
# ═══════════════════════════════════════════════════════

async def create_payment(
    user_id: int, amount: int, receipt_file_id: str, receipt_type: str
) -> int:
    return await db.insert(
        "INSERT INTO payments(user_id, amount, receipt_file_id, receipt_type) "
        "VALUES(?, ?, ?, ?)",
        (user_id, amount, receipt_file_id, receipt_type),
    )


async def get_payment(pid: int) -> dict[str, Any] | None:
    return _row(await db.fetchone("SELECT * FROM payments WHERE id = ?", (pid,)))


async def approve_payment(pid: int, admin_id: int) -> dict[str, Any] | None:
    """pending → approved (atomik). Faqat birinchi admin bajaradi."""
    row = await db.returning(
        "UPDATE payments SET status = 'approved', handled_by = ?, handled_at = ? "
        "WHERE id = ? AND status = 'pending' RETURNING user_id, amount",
        (admin_id, _now(), pid),
    )
    return {"user_id": row[0], "amount": row[1]} if row else None


async def reject_payment(pid: int, admin_id: int, reason: str) -> dict[str, Any] | None:
    row = await db.returning(
        "UPDATE payments SET status = 'rejected', handled_by = ?, handled_at = ?, "
        "reason = ? WHERE id = ? AND status = 'pending' RETURNING user_id, amount",
        (admin_id, _now(), reason, pid),
    )
    return {"user_id": row[0], "amount": row[1]} if row else None


# ═══════════════════════════════════════════════════════
#              YORDAM (ADMIN BILAN ALOQA) LIMITI
# ═══════════════════════════════════════════════════════

HELP_WINDOW = 12 * 3600  # 12 soat


def help_limit() -> int:
    return int(get_setting("help_limit", "5") or 5)


async def help_state(tid: int) -> tuple[int, int]:
    """(ishlatilgan, oyna_boshlanishi) — oyna tugagan bo'lsa (0, hozir)."""
    now = _now()
    row = await db.fetchone(
        "SELECT count, window_start FROM help_usage WHERE user_id = ?", (tid,)
    )
    if row is None or now - row["window_start"] >= HELP_WINDOW:
        return 0, now
    return int(row["count"]), int(row["window_start"])


async def help_consume(tid: int) -> tuple[bool, int, int]:
    """Bitta xabar «sarflaydi». → (ruxsat, qolgan, tiklanish_vaqti)."""
    now = _now()
    limit = help_limit()
    row = await db.fetchone(
        "SELECT count, window_start FROM help_usage WHERE user_id = ?", (tid,)
    )
    if row is None or now - row["window_start"] >= HELP_WINDOW:
        count, ws = 0, now
    else:
        count, ws = int(row["count"]), int(row["window_start"])

    if count >= limit:
        return False, 0, ws + HELP_WINDOW

    count += 1
    await db.execute(
        "INSERT INTO help_usage(user_id, count, window_start) VALUES(?, ?, ?) "
        "ON CONFLICT(user_id) DO UPDATE SET count = excluded.count, "
        "window_start = excluded.window_start",
        (tid, count, ws),
    )
    return True, limit - count, ws + HELP_WINDOW


# ═══════════════════════════════════════════════════════
#                    REFERAL DASTURI
# ═══════════════════════════════════════════════════════

def referral_price() -> int:
    return int(get_setting("referral_price", "0") or 0)


async def capture_referral(referrer_id: int, referred_id: int) -> None:
    """Yangi foydalanuvchi taklif havolasi orqali kelganda yozib qo'yadi.

    Faqat YANGI foydalanuvchi uchun chaqiriladi. Mukofot hali berilmaydi —
    foydalanuvchi majburiy obunadan o'tgach beriladi (claim_referral).
    """
    if referrer_id == referred_id:
        return
    # Taklif qiluvchi haqiqiy (ro'yxatdan o'tgan) foydalanuvchi bo'lishi shart.
    if await get_user(referrer_id) is None:
        return
    await db.execute(
        "INSERT OR IGNORE INTO referrals(referrer_id, referred_id) VALUES(?, ?)",
        (referrer_id, referred_id),
    )


async def has_pending_referral(referred_id: int) -> bool:
    row = await db.fetchone(
        "SELECT 1 FROM referrals WHERE referred_id = ? AND rewarded = 0", (referred_id,)
    )
    return row is not None


async def claim_referral(referred_id: int) -> dict[str, Any] | None:
    """Taklif qilingan foydalanuvchi obunadan o'tdi → mukofotni «band qiladi».

    Atomik: bir vaqtda ikki marta chaqirilsa ham faqat bittasi mukofot beradi.
    → {referrer_id, reward} yoki None (allaqachon berilgan / topilmadi).
    """
    reward = referral_price()
    row = await db.returning(
        "UPDATE referrals SET rewarded = 1, reward = ? "
        "WHERE referred_id = ? AND rewarded = 0 RETURNING referrer_id",
        (reward, referred_id),
    )
    if row is None:
        return None
    return {"referrer_id": row[0], "reward": reward}


async def referral_count(referrer_id: int) -> int:
    return await db.fetchval(
        "SELECT COUNT(*) FROM referrals WHERE referrer_id = ? AND rewarded = 1",
        (referrer_id,),
        default=0,
    )


async def referral_earned(referrer_id: int) -> int:
    return await db.fetchval(
        "SELECT COALESCE(SUM(reward), 0) FROM referrals WHERE referrer_id = ? AND rewarded = 1",
        (referrer_id,),
        default=0,
    )


# ═══════════════════════════════════════════════════════
#                       KANALLAR
# ═══════════════════════════════════════════════════════

async def load_channels() -> None:
    _channels.clear()
    for ctype in ("base", "mandatory", "request"):
        _channels[ctype] = []
    for row in await db.fetchall("SELECT * FROM channels ORDER BY id"):
        _channels.setdefault(row["ctype"], []).append(dict(row))


def get_channels(ctype: Literal["base", "mandatory", "request"]) -> list[dict[str, Any]]:
    """Xotiradan — obuna tekshiruvida har safar chaqiriladi."""
    return _channels.get(ctype, [])


def base_channel() -> dict[str, Any] | None:
    chans = _channels.get("base") or []
    return chans[0] if chans else None


def sub_channels() -> list[dict[str, Any]]:
    """Obuna panelida ko'rinadigan barcha kanallar (mandatory + request)."""
    return get_channels("mandatory") + get_channels("request")


def channel_exists(chat_id: int) -> bool:
    return any(c["chat_id"] == chat_id for group in _channels.values() for c in group)


def get_channel_by_id(row_id: int) -> dict[str, Any] | None:
    for group in _channels.values():
        for chan in group:
            if chan["id"] == row_id:
                return chan
    return None


async def add_channel(
    chat_id: int,
    username: str | None,
    title: str,
    ctype: str,
    invite_link: str | None = None,
) -> None:
    await db.execute(
        "INSERT INTO channels(chat_id, username, title, ctype, invite_link) "
        "VALUES(?, ?, ?, ?, ?)",
        (chat_id, username, title, ctype, invite_link),
    )
    await load_channels()


async def delete_channel(row_id: int) -> bool:
    changed = await db.execute("DELETE FROM channels WHERE id = ?", (row_id,))
    if changed:
        await load_channels()
    return bool(changed)


async def update_channel_title(row_id: int, title: str) -> bool:
    """Obuna panelidagi tugmada ko'rinadigan nomni o'zgartiradi."""
    changed = await db.execute(
        "UPDATE channels SET title = ? WHERE id = ?", (title, row_id)
    )
    if changed:
        await load_channels()
    return bool(changed)


async def update_channel_chat(
    row_id: int, chat_id: int, username: str | None, invite_link: str | None
) -> bool:
    """Kanalning chat ma'lumotlarini yangilaydi (username o'zgarganda / almashtirganda)."""
    changed = await db.execute(
        "UPDATE channels SET chat_id = ?, username = ?, invite_link = ? WHERE id = ?",
        (chat_id, username, invite_link, row_id),
    )
    if changed:
        await load_channels()
    return bool(changed)


def channel_stats() -> dict[str, int]:
    return {
        "base": len(get_channels("base")),
        "mandatory": len(get_channels("mandatory")),
        "request": len(get_channels("request")),
    }


# ═══════════════════════════════════════════════════════
#                      ZAYAVKALAR
# ═══════════════════════════════════════════════════════

async def add_join_request(user_id: int, chat_id: int) -> None:
    await db.execute(
        "INSERT OR IGNORE INTO join_requests(user_id, chat_id) VALUES(?, ?)",
        (user_id, chat_id),
    )


async def join_request_chats(user_id: int) -> set[int]:
    """Foydalanuvchi so'rov yuborgan barcha kanallar — bitta so'rovda."""
    rows = await db.fetchall(
        "SELECT chat_id FROM join_requests WHERE user_id = ?", (user_id,)
    )
    return {r["chat_id"] for r in rows}


async def drop_join_requests(chat_id: int) -> None:
    await db.execute("DELETE FROM join_requests WHERE chat_id = ?", (chat_id,))


# ═══════════════════════════════════════════════════════
#                   BUFERLARNI TASHLASH
# ═══════════════════════════════════════════════════════

async def flush_buffers() -> None:
    """Yig'ilgan ko'rishlar va last_seen'ni bitta tranzaksiyada yozadi.

    Rejalashtiruvchi har 30 sekundda va bot to'xtaganda chaqiradi.
    """
    views = dict(_views_buf)
    _views_buf.clear()
    seen = dict(_seen_buf)
    _seen_buf.clear()

    if not views and not seen:
        return

    try:
        async with db.transaction() as conn:
            if views:
                await conn.executemany(
                    "UPDATE content SET views = views + ? WHERE code = ?",
                    [(count, code) for code, count in views.items()],
                )
            if seen:
                await conn.executemany(
                    "UPDATE users SET last_seen = ? WHERE telegram_id = ?",
                    [(ts, tid) for tid, ts in seen.items()],
                )
    except Exception:
        # Yozib bo'lmadi — ma'lumot yo'qolmasin, buferga qaytaramiz.
        for code, count in views.items():
            _views_buf[code] = _views_buf.get(code, 0) + count
        for tid, ts in seen.items():
            _seen_buf.setdefault(tid, ts)
        log.exception("Buferlarni tashlashda xato")
        return

    log.debug("Bufer tashlandi: %d ko'rish, %d last_seen", len(views), len(seen))


async def warmup() -> None:
    """Startda barcha issiq keshlarni to'ldiradi."""
    await load_settings()
    await load_admins()
    await load_channels()
