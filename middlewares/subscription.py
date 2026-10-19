"""Majburiy obuna middleware'i — faqat foydalanuvchi routerlariga ulanadi.

Tezlik: `check_subscription` keshdan o'tadi — obuna bo'lgan foydalanuvchi uchun
Telegram API'ga BIRORTA ham so'rov ketmaydi (utils/helpers.py ga qarang).

💎 ISTISNO: «Obunasiz ko'rish» yo'li. Premium obunachilar majburiy obunadan
ozod bo'lgani uchun, obunasiz foydalanuvchi ham premium SOTIB OLA olishi kerak —
aks holda obuna panelidagi tugma boshi berk ko'chaga olib borardi. Shu bois
premium tanlash/tasdiqlash tugmalari va balans to'ldirish jarayoni (summa + chek)
to'siqdan o'tkaziladi. Kontent (kod, qism, ko'rish) esa avvalgidek himoyalangan.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import CallbackQuery, Message, TelegramObject, User

from database import queries as q
from keyboards.user_kb import subscription_kb
from states.admin_states import TopUpSG
from utils import texts
from utils.helpers import subscription_gate

# Obuna tekshiruvidan ozod: obuna panelining o'zi va admin kirishi.
_EXEMPT_CALLBACKS = frozenset(
    {"check_sub", "noop", "nosub", "backsub", "premno", "topup", "ucancel"}
)

# 💎 «Obunasiz ko'rish» yo'li: obunasiz foydalanuvchi ham premium sotib olishi
# va shu uchun balansini to'ldirishi SHART — aks holda tugma ma'nosiz bo'lardi.
_EXEMPT_PREFIXES = ("prem:", "premyes:")

# Balans to'ldirish jarayonidagi xabarlar (summa, chek) ham o'tkaziladi.
_EXEMPT_STATES = frozenset({TopUpSG.amount.state, TopUpSG.receipt.state})


class SubscriptionMiddleware(BaseMiddleware):
    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        user: User | None = data.get("event_from_user")
        if user is None or user.is_bot:
            return await handler(event, data)

        # Adminlar va «Tekshirish» tugmasi — o'tkazib yuboriladi.
        if q.is_admin(user.id):
            return await handler(event, data)
        if isinstance(event, CallbackQuery):
            cb = event.data or ""
            if cb in _EXEMPT_CALLBACKS or cb.startswith(_EXEMPT_PREFIXES):
                return await handler(event, data)
        elif isinstance(event, Message):
            fsm = data.get("state")
            if fsm is not None and await fsm.get_state() in _EXEMPT_STATES:
                return await handler(event, data)

        bot = data["bot"]
        missing = await subscription_gate(bot, user.id)
        if not missing:
            return await handler(event, data)

        # Panelda FAQAT yetishmayotgan kanallar — allaqachon obuna bo'lganlari
        # qayta ko'rsatilmaydi.
        kb = subscription_kb(missing)
        if isinstance(event, CallbackQuery):
            await event.answer(texts.sub_not_enough(len(missing)), show_alert=True)
            await event.message.answer(texts.SUBSCRIPTION_PANEL, reply_markup=kb)
        elif isinstance(event, Message):
            await event.answer(texts.SUBSCRIPTION_PANEL, reply_markup=kb)
        return None
