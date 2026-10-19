"""/start, deep link, va tizim hodisalari (my_chat_member, chat_join_request)."""

from __future__ import annotations

import logging

from aiogram import Bot, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.filters import CommandObject, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import ChatJoinRequest, ChatMemberUpdated, Message
from aiogram.filters.chat_member_updated import (
    ADMINISTRATOR,
    IS_NOT_MEMBER,
    KICKED,
    LEFT,
    MEMBER,
    ChatMemberUpdatedFilter,
)

from config import config
from database import queries as q
from keyboards.user_kb import subscription_kb, user_menu
from utils import texts
from utils.helpers import (
    fire_and_forget,
    hhmm,
    invalidate_subscription,
    notify_admins,
    reward_referrer,
    subscription_gate,
)

log = logging.getLogger(__name__)
router = Router(name="user:start")


async def _register_and_notify(bot: Bot, message: Message) -> bool:
    """Foydalanuvchini yozadi va (yangi bo'lsa) adminlarga xabar beradi. → is_new."""
    user = message.from_user
    is_new = await q.register_user(user.id, user.username, user.full_name)
    if is_new:
        # Fon vazifasi — foydalanuvchi adminlarga xabar ketishini kutib turmasin.
        fire_and_forget(
            notify_admins(
                bot,
                texts.new_user_alert(user.full_name, user.username, user.id, hhmm()),
            )
        )
    return is_new


@router.message(CommandStart(deep_link=True))
async def start_deeplink(message: Message, command: CommandObject, state: FSMContext, bot: Bot):
    """t.me/Bot?start=10001 → kontent · ?start=ref_<id> → referal havolasi."""
    await state.clear()
    is_new = await _register_and_notify(bot, message)

    payload = (command.args or "").strip()
    # Referal havolasi: faqat YANGI foydalanuvchi taklif sifatida yoziladi.
    if is_new and payload.startswith("ref_") and payload[4:].isdigit():
        await q.capture_referral(int(payload[4:]), message.from_user.id)

    missing = await subscription_gate(bot, message.from_user.id)
    if missing:
        # Panelda faqat obuna bo'lMAGAN kanallar ko'rsatiladi.
        await message.answer(texts.SUBSCRIPTION_PANEL, reply_markup=subscription_kb(missing))
        return

    # Obunadan o'tdi → taklif qiluvchiga mukofot (kutilayotgan referal bo'lsa).
    await reward_referrer(bot, message.from_user.id)

    if payload.isdigit():
        # content.py dagi yuborish funksiyasini qayta ishlatamiz.
        from handlers.user.content import deliver

        if await deliver(message, bot, int(payload)):
            await message.answer(texts.welcome(message.from_user.full_name), reply_markup=user_menu())
            return

    await message.answer(texts.welcome(message.from_user.full_name), reply_markup=user_menu())


@router.message(CommandStart())
async def start(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    await _register_and_notify(bot, message)

    missing = await subscription_gate(bot, message.from_user.id)
    if missing:
        await message.answer(
            texts.SUBSCRIPTION_PANEL, reply_markup=subscription_kb(missing)
        )
        return

    # Obunadan o'tgan bo'lsa — kutilayotgan referal mukofotini beramiz.
    await reward_referrer(bot, message.from_user.id)

    await message.answer(texts.welcome(message.from_user.full_name), reply_markup=user_menu())


# ═══════════════════════════════════════════════════════
#              BOTNI BLOKLASH / TARK ETISH
# ═══════════════════════════════════════════════════════

@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=KICKED))
async def bot_blocked(event: ChatMemberUpdated, bot: Bot):
    """Foydalanuvchi botni bloklab qo'ydi → 🔴 bildirishnoma."""
    user = event.from_user
    await q.set_status(user.id, "blocked")
    fire_and_forget(
        notify_admins(bot, texts.left_user_alert(user.full_name, user.id, hhmm()))
    )


@router.my_chat_member(ChatMemberUpdatedFilter(member_status_changed=MEMBER))
async def bot_unblocked(event: ChatMemberUpdated):
    """Qayta ishga tushirdi → yana faol."""
    await q.set_status(event.from_user.id, "active")


# ═══════════════════════════════════════════════════════
#                      ZAYAVKA
# ═══════════════════════════════════════════════════════

@router.chat_join_request()
async def join_request(event: ChatJoinRequest, bot: Bot):
    """So'rov yuborilishi bilan obuna hisoblanadi (TZ §7.2)."""
    await q.add_join_request(event.from_user.id, event.chat.id)
    # Kesh bekor qilinadi → foydalanuvchi darhol o'tadi, kutmaydi.
    invalidate_subscription(event.from_user.id, event.chat.id)

    if config.auto_approve:
        try:
            await event.approve()
        except TelegramAPIError as e:
            log.warning("Zayavkani avtomatik qabul qilib bo'lmadi: %s", e)


# ═══════════════════════════════════════════════════════
#          OBUNA KESHINI REAL VAQTDA BEKOR QILISH
# ═══════════════════════════════════════════════════════

@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=(LEFT | KICKED | IS_NOT_MEMBER))
)
async def user_left_channel(event: ChatMemberUpdated):
    """Kanaldan chiqdi → keshni darhol tozalaymiz.

    Shu tufayli obuna keshi uzoq TTL bilan ishlashi mumkin: chiqib ketgan
    foydalanuvchi keyingi harakatida obuna panelini KO'RADI, TTL kutilmaydi.
    """
    invalidate_subscription(event.from_user.id, event.chat.id)


@router.chat_member(
    ChatMemberUpdatedFilter(member_status_changed=(MEMBER | ADMINISTRATOR))
)
async def user_joined_channel(event: ChatMemberUpdated):
    """Kanalga qo'shildi → keshni tozalaymiz, «Tekshirish» darhol o'tadi."""
    invalidate_subscription(event.from_user.id, event.chat.id)
