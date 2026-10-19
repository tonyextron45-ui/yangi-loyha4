"""Sozlamalarni .env faylidan o'qish."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")


def _bool(key: str, default: bool = False) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on", "ha"}


def _int(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True, slots=True)
class Config:
    bot_token: str
    main_admin_id: int
    admin_password: str
    db_path: Path

    # Turso (bulut SQLite) — bo'sh bo'lsa lokal fayl ishlatiladi
    turso_url: str
    turso_token: str

    # Health-server porti (Render $PORT beradi)
    port: int

    auto_approve: bool
    protect_content: bool
    sub_cache_ttl: int

    # Kod generatsiyasi
    start_code: int = 10000

    # Pagination
    episodes_per_page: int = 5
    users_per_page: int = 10

    # Parol himoyasi
    max_password_tries: int = 3
    password_lock_minutes: int = 5

    # Broadcast tezligi (Telegram limiti ~30/sek, xavfsiz chegara)
    broadcast_rate: int = 25
    broadcast_workers: int = 12


def load_config() -> Config:
    token = os.getenv("BOT_TOKEN", "").strip()
    if not token:
        raise RuntimeError(
            "BOT_TOKEN topilmadi! .env.example faylidan .env yarating va token kiriting."
        )

    main_admin = _int("MAIN_ADMIN_ID", 0)
    if not main_admin:
        raise RuntimeError("MAIN_ADMIN_ID topilmadi! .env faylida ko'rsating.")

    db_path = Path(os.getenv("DB_PATH", "kinobot.db"))
    if not db_path.is_absolute():
        db_path = BASE_DIR / db_path

    return Config(
        bot_token=token,
        main_admin_id=main_admin,
        admin_password=os.getenv("ADMIN_PASSWORD", "090704").strip(),
        db_path=db_path,
        turso_url=os.getenv("TURSO_DATABASE_URL", "").strip(),
        turso_token=os.getenv("TURSO_AUTH_TOKEN", "").strip(),
        port=_int("PORT", 8080),
        auto_approve=_bool("AUTO_APPROVE", False),
        protect_content=_bool("PROTECT_CONTENT", False),
        sub_cache_ttl=_int("SUB_CACHE_TTL", 600),
    )


config = load_config()


def db_url() -> tuple[str, str | None]:
    """(url, auth_token) — Turso sozlangan bo'lsa u, aks holda lokal fayl."""
    if config.turso_url:
        return config.turso_url, (config.turso_token or None)
    return f"file:{config.db_path.as_posix()}", None

