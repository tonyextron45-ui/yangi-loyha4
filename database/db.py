"""Ma'lumotlar bazasi qatlami — libSQL (SQLite mos) ustida.

Bitta kod IKKI muhitda ishlaydi:
  • Lokal ishlab chiqish → `file:...` (oddiy SQLite fayl, tez)
  • Render/bulut        → `libsql://...` (Turso — bepul, doimiy saqlash)

Turso remote bo'lgani uchun WAL/pragma sozlamalari kerak emas (serverda hal
qilinadi). Trafik/tezlik queries.py dagi kesh qatlami hisobiga saqlanadi:
adminlar, kanallar, sozlamalar, kontent va obuna holati xotirada, shuning uchun
foydalanuvchi harakatlarining ko'pi DB'ga UMUMAN bormaydi. Yozuvlar esa
buferlanib, 30 sekundda BITTA `batch` (tranzaksiya) bilan tashlanadi.
"""

from __future__ import annotations

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import Any, AsyncIterator, Iterable, Sequence

import libsql_client

from config import config, db_url

log = logging.getLogger(__name__)


# ─────────────── Row o'ralmasi (sqlite3.Row bilan mos) ───────────────

class Row:
    """int/str indeks, keys(), dict(row) — queries.py o'zgarmasligi uchun."""

    __slots__ = ("_cols", "_vals", "_idx")

    def __init__(self, cols: Sequence[str], vals: list[Any]) -> None:
        self._cols = cols
        self._vals = vals
        self._idx: dict[str, int] | None = None

    def _index(self) -> dict[str, int]:
        if self._idx is None:
            self._idx = {c: i for i, c in enumerate(self._cols)}
        return self._idx

    def __getitem__(self, key: int | str) -> Any:
        if isinstance(key, int):
            return self._vals[key]
        return self._vals[self._index()[key]]

    def keys(self) -> Sequence[str]:
        return self._cols

    def get(self, key: str, default: Any = None) -> Any:
        idx = self._index().get(key)
        return self._vals[idx] if idx is not None else default

    def __contains__(self, key: str) -> bool:
        return key in self._index()

    def __iter__(self):
        return iter(self._vals)

    def __len__(self) -> int:
        return len(self._vals)


# ─────────────── Sxema (har biri alohida statement) ───────────────

SCHEMA: tuple[str, ...] = (
    """
    CREATE TABLE IF NOT EXISTS users (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id     INTEGER UNIQUE NOT NULL,
        username        TEXT,
        full_name       TEXT,
        status          TEXT    NOT NULL DEFAULT 'active',
        is_banned       INTEGER NOT NULL DEFAULT 0,
        ban_until       INTEGER,
        balance         INTEGER NOT NULL DEFAULT 0,
        premium_until   INTEGER,
        premium_tariff  TEXT,
        premium_started INTEGER,
        joined_at       INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        last_seen       INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_users_status ON users(status)",
    "CREATE INDEX IF NOT EXISTS idx_users_ban ON users(ban_until) WHERE is_banned = 1",
    "CREATE INDEX IF NOT EXISTS idx_users_id ON users(id)",
    """
    CREATE TABLE IF NOT EXISTS admins (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        telegram_id  INTEGER UNIQUE NOT NULL,
        role         TEXT    NOT NULL DEFAULT 'helper',
        can_content  INTEGER NOT NULL DEFAULT 0,
        can_channels INTEGER NOT NULL DEFAULT 0,
        can_admins   INTEGER NOT NULL DEFAULT 0,
        is_active    INTEGER NOT NULL DEFAULT 1,
        added_at     INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS content (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        code            INTEGER UNIQUE NOT NULL,
        ctype           TEXT    NOT NULL,
        title           TEXT,
        caption         TEXT    NOT NULL,
        file_id         TEXT,
        base_msg_id     INTEGER,
        trailer_file_id TEXT,
        trailer_type    TEXT,
        trailer_msg_id  INTEGER,
        is_paid         INTEGER NOT NULL DEFAULT 0,
        price           INTEGER NOT NULL DEFAULT 0,
        views           INTEGER NOT NULL DEFAULT 0,
        is_deleted      INTEGER NOT NULL DEFAULT 0,
        added_by        INTEGER,
        created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_content_live ON content(ctype) WHERE is_deleted = 0",
    "CREATE INDEX IF NOT EXISTS idx_content_top ON content(views DESC) WHERE is_deleted = 0",
    """
    CREATE TABLE IF NOT EXISTS episodes (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        series_code INTEGER NOT NULL REFERENCES content(code) ON DELETE CASCADE,
        ep_number   INTEGER NOT NULL,
        file_id     TEXT    NOT NULL,
        base_msg_id INTEGER,
        UNIQUE (series_code, ep_number)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_episodes_code ON episodes(series_code, ep_number)",
    """
    CREATE TABLE IF NOT EXISTS channels (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        chat_id     INTEGER UNIQUE NOT NULL,
        username    TEXT,
        title       TEXT,
        ctype       TEXT    NOT NULL,
        invite_link TEXT,
        added_at    INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_channels_type ON channels(ctype)",
    """
    CREATE TABLE IF NOT EXISTS join_requests (
        user_id    INTEGER NOT NULL,
        chat_id    INTEGER NOT NULL,
        created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        PRIMARY KEY (user_id, chat_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        key   TEXT PRIMARY KEY,
        value TEXT NOT NULL
    )
    """,
    # ─── Pullik kontent: sotib olishlar (kod bo'yicha, 1 marta) ───
    """
    CREATE TABLE IF NOT EXISTS purchases (
        id         INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        code       INTEGER NOT NULL,
        price      INTEGER NOT NULL DEFAULT 0,
        created_at INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        UNIQUE (user_id, code)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_purchases_user ON purchases(user_id)",
    # ─── To'lov kartalari (admin) ───
    """
    CREATE TABLE IF NOT EXISTS cards (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        number   TEXT NOT NULL,
        holder   TEXT NOT NULL,
        added_at INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    # ─── Balans to'ldirish so'rovlari (chek bilan) ───
    """
    CREATE TABLE IF NOT EXISTS payments (
        id              INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id         INTEGER NOT NULL,
        amount          INTEGER NOT NULL,
        receipt_file_id TEXT,
        receipt_type    TEXT,
        status          TEXT    NOT NULL DEFAULT 'pending',
        reason          TEXT,
        created_at      INTEGER NOT NULL DEFAULT (strftime('%s','now')),
        handled_by      INTEGER,
        handled_at      INTEGER
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_payments_status ON payments(status)",
    # ─── Yordam (admin bilan aloqa) limiti — 12 soatlik oyna ───
    """
    CREATE TABLE IF NOT EXISTS help_usage (
        user_id      INTEGER PRIMARY KEY,
        count        INTEGER NOT NULL DEFAULT 0,
        window_start INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    # ─── Referal dasturi: har bir taklif qilingan (yangi) foydalanuvchi ───
    """
    CREATE TABLE IF NOT EXISTS referrals (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        referrer_id INTEGER NOT NULL,
        referred_id INTEGER UNIQUE NOT NULL,
        reward      INTEGER NOT NULL DEFAULT 0,
        rewarded    INTEGER NOT NULL DEFAULT 0,
        created_at  INTEGER NOT NULL DEFAULT (strftime('%s','now'))
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_referrals_referrer ON referrals(referrer_id)",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('code_counter', '9999')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('notifications', 'off')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('tariff_1m', '10000')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('tariff_3m', '25000')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('tariff_6m', '45000')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('tariff_1y', '80000')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('help_limit', '5')",
    "INSERT OR IGNORE INTO settings(key, value) VALUES ('referral_price', '1000')",
)

# Migratsiya: eski bazaga qo'shiladigan ustunlar.
_MIGRATIONS: tuple[tuple[str, str, str], ...] = (
    ("content", "title", "TEXT"),
    ("content", "trailer_file_id", "TEXT"),
    ("content", "trailer_type", "TEXT"),
    ("content", "trailer_msg_id", "INTEGER"),
    ("content", "is_paid", "INTEGER NOT NULL DEFAULT 0"),
    ("content", "price", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "balance", "INTEGER NOT NULL DEFAULT 0"),
    ("users", "premium_until", "INTEGER"),
    ("users", "premium_tariff", "TEXT"),
    ("users", "premium_started", "INTEGER"),
    ("payments", "reason", "TEXT"),
)


class _BatchCollector:
    """transaction() ichida yozuvlarni yig'adi — BITTA batch bilan atomik bajariladi."""

    __slots__ = ("stmts",)

    def __init__(self) -> None:
        self.stmts: list[tuple[str, list[Any]]] = []

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> None:
        self.stmts.append((sql, list(params)))

    async def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> None:
        for params in seq:
            self.stmts.append((sql, list(params)))


class Database:
    """queries.py kutadigan interfeys — libSQL (lokal fayl yoki Turso) ustida."""

    __slots__ = ("_url", "_auth", "_client", "_wlock", "_ready")

    def __init__(self, url: str, auth_token: str | None) -> None:
        self._url = url
        self._auth = auth_token
        self._client: libsql_client.Client | None = None
        self._wlock = asyncio.Lock()
        self._ready = False

    # ─────────────── hayot sikli ───────────────

    async def connect(self) -> None:
        if self._ready:
            return
        # `libsql://` sxemasi WebSocket (wss) ishlatadi — ba'zi tarmoqlar/proksilar
        # uni bloklaydi. `https://` (HTTP transport) hamma joyda ishonchli ishlaydi,
        # shuning uchun avtomatik o'giramiz.
        url = self._url
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self._client = libsql_client.create_client(url=url, auth_token=self._auth)
        await self._client.execute("SELECT 1")  # ulanish tekshiruvi

        for stmt in SCHEMA:
            await self._client.execute(stmt)
        await self._migrate()

        # Migratsiyadan KEYIN — yangi (ALTER bilan qo'shilgan) ustunga bog'liq indeks.
        # Eski bazada `premium_until` ustuni faqat _migrate() dan so'ng paydo bo'ladi.
        await self._client.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_premium ON users(premium_until) "
            "WHERE premium_until IS NOT NULL"
        )

        self._ready = True
        kind = "Turso (bulut)" if self._url.startswith(("libsql:", "http", "ws")) else "lokal fayl"
        log.info("Baza tayyor: %s", kind)

    async def _migrate(self) -> None:
        # ALTER'dan OLDIN mavjud ustunlarni tekshiramiz — shunda dublikat xato
        # umuman chiqmaydi (libsql HTTP transporti xato javobni noto'g'ri
        # qaytaradigan holatdan qochamiz).
        by_table: dict[str, list[tuple[str, str]]] = {}
        for table, name, decl in _MIGRATIONS:
            by_table.setdefault(table, []).append((name, decl))

        for table, cols in by_table.items():
            rs = await self._client.execute(f"PRAGMA table_info({table})")
            existing = {r[1] for r in rs.rows}  # r[1] = ustun nomi
            for name, decl in cols:
                if name not in existing:
                    await self._client.execute(
                        f"ALTER TABLE {table} ADD COLUMN {name} {decl}"
                    )
                    log.info("Migratsiya: %s.%s ustuni qo'shildi", table, name)

    async def close(self) -> None:
        if not self._ready or self._client is None:
            return
        self._ready = False
        await self._client.close()

    # ─────────────── o'qish ───────────────

    def _wrap(self, rs: Any) -> list[Row]:
        cols = rs.columns
        return [Row(cols, list(r)) for r in rs.rows]

    async def fetchall(self, sql: str, params: Sequence[Any] = ()) -> list[Row]:
        rs = await self._client.execute(sql, list(params))
        return self._wrap(rs)

    async def fetchone(self, sql: str, params: Sequence[Any] = ()) -> Row | None:
        rs = await self._client.execute(sql, list(params))
        rows = self._wrap(rs)
        return rows[0] if rows else None

    async def fetchval(self, sql: str, params: Sequence[Any] = (), default: Any = None) -> Any:
        row = await self.fetchone(sql, params)
        return default if row is None else row[0]

    # ─────────────── yozish (navbat bilan) ───────────────

    async def execute(self, sql: str, params: Sequence[Any] = ()) -> int:
        async with self._wlock:
            rs = await self._client.execute(sql, list(params))
        return rs.rows_affected

    async def executemany(self, sql: str, seq: Iterable[Sequence[Any]]) -> None:
        stmts = [(sql, list(p)) for p in seq]
        if not stmts:
            return
        async with self._wlock:
            await self._client.batch(stmts)

    async def returning(self, sql: str, params: Sequence[Any] = ()) -> Row | None:
        """RETURNING bandli yozuv — birinchi qatorni qaytaradi."""
        async with self._wlock:
            rs = await self._client.execute(sql, list(params))
        rows = self._wrap(rs)
        return rows[0] if rows else None

    async def insert(self, sql: str, params: Sequence[Any] = ()) -> int:
        async with self._wlock:
            rs = await self._client.execute(sql, list(params))
        return rs.last_insert_rowid

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[_BatchCollector]:
        """Atomik blok — ichidagi barcha yozuv BITTA batch bilan bajariladi."""
        collector = _BatchCollector()
        yield collector
        if collector.stmts:
            async with self._wlock:
                await self._client.batch(collector.stmts)

    async def optimize(self) -> None:
        """Davriy texnik xizmat — remote'da kerak emas, lokalda foydali."""
        try:
            await self._client.execute("PRAGMA optimize")
        except Exception:  # noqa: BLE001
            pass


# Yagona global nusxa — `from database.db import db` hamma joyda shu obyektni beradi.
_url, _auth = db_url()
db = Database(_url, _auth)
