"""Maxsus filtrlar — barchasi xotiradan ishlaydi, DB'ga bormaydi."""

from __future__ import annotations

from typing import Literal

from aiogram.filters import BaseFilter
from aiogram.types import CallbackQuery, Message, TelegramObject

from database import queries as q


class IsAdmin(BaseFilter):
    """Router darajasida qo'llanadi — admin bo'lmagan update umuman kirmaydi."""

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and q.is_admin(user.id)


class HasPerm(BaseFilter):
    """Huquq tekshiruvi. Huquq yo'q bo'lsa alert chiqaradi va to'xtatadi."""

    def __init__(self, perm: Literal["content", "channels", "admins"]) -> None:
        self.perm = perm

    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        if user is None:
            return False
        if q.has_perm(user.id, self.perm):
            return True

        from utils import texts

        if isinstance(event, CallbackQuery):
            await event.answer(texts.NO_PERMISSION, show_alert=True)
        elif isinstance(event, Message):
            await event.answer(texts.NO_PERMISSION)
        return False


class IsMainAdmin(BaseFilter):
    async def __call__(self, event: TelegramObject) -> bool:
        user = getattr(event, "from_user", None)
        return user is not None and q.is_main_admin(user.id)
