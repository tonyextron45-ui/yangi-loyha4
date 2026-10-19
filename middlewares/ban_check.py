"""Bloklangan foydalanuvchini to'xtatuvchi middleware.

Tezlik: foydalanuvchi keshdan olinadi (TTL 300s), ya'ni har bir update'da
DB'ga so'rov ketmaydi. Bloklanganda kesh darhol bekor qilinadi.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from database import queries as q
from utils import texts
from utils.helpers import minutes_left


class BanCheckMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)

        # Adminlarni bloklab bo'lmaydi.
        if q.is_admin(user.id):
            return await handler(event, data)

        db_user = await q.get_user(user.id)
        if db_user is None or not db_user["is_banned"]:
            return await handler(event, data)

        left = minutes_left(db_user["ban_until"])
        if left <= 0:
            # Muddat tugagan — rejalashtiruvchini kutmasdan darhol ochamiz.
            await q.unban_user(user.id)
            return await handler(event, data)

        text = texts.ban_active(left)
        if isinstance(event, CallbackQuery):
            await event.answer(
                f"⛔️ Siz bloklangansiz!\n⏳ Qolgan vaqt: {left} daqiqa", show_alert=True
            )
        elif isinstance(event, Message):
            await event.answer(text)
        return None  # zanjir shu yerda uziladi
