"""Majburiy obuna paneli, «✅ Tekshirish» va «💎 Obunasiz ko'rish» tugmalari."""

from __future__ import annotations

import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery

from database import queries as q
from keyboards.user_kb import premium_tariffs_kb, subscription_kb, user_menu
from utils import texts
from utils.helpers import invalidate_subscription, reward_referrer, subscription_gate

router = Router(name="user:subscription")


@router.callback_query(F.data == "check_sub")
async def check_sub(call: CallbackQuery, bot: Bot):
    # Tugma bosildi = holat o'zgargan bo'lishi mumkin → keshni majburan yangilaymiz.
    invalidate_subscription(call.from_user.id)
    for chan in q.sub_channels():
        invalidate_subscription(call.from_user.id, chan["chat_id"])

    missing = await subscription_gate(bot, call.from_user.id)
    if missing:
        await call.answer(texts.sub_not_enough(len(missing)), show_alert=True)
        # Panel yangilanadi: obuna bo'lingan kanallar ro'yxatdan chiqib ketadi,
        # faqat qolganlari ko'rinadi. Matn o'zgarmasa Telegram edit'ni rad etadi.
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_text(
                texts.SUBSCRIPTION_PANEL, reply_markup=subscription_kb(missing)
            )
        return

    # Majburiy obunadan o'tdi → taklif qiluvchiga referal mukofoti (bo'lsa).
    await reward_referrer(bot, call.from_user.id)

    await call.answer("🎉 Obuna tasdiqlandi!")
    await call.message.edit_text(texts.SUB_CONFIRMED)
    await call.message.answer(texts.welcome(call.from_user.full_name), reply_markup=user_menu())


@router.callback_query(F.data == "nosub")
async def nosub_premium(call: CallbackQuery, state: FSMContext, bot: Bot):
    """«💎 Obunasiz ko'rish» — majburiy obuna o'rniga premium taklifi.

    Premium obunachilar to'siqdan ozod (helpers.subscription_gate), shuning uchun
    bu tugma foydalanuvchini to'g'ridan-to'g'ri tarif tanlashga olib boradi.
    """
    await state.clear()

    # Ehtiyot chorasi: obuna oralig'ida faollashgan bo'lsa — panel yopiladi.
    if not await subscription_gate(bot, call.from_user.id):
        with contextlib.suppress(TelegramBadRequest):
            await call.message.delete()
        await call.message.answer(
            texts.welcome(call.from_user.full_name), reply_markup=user_menu()
        )
        await call.answer()
        return

    prices = q.tariff_prices()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.premium_gate_panel(prices),
            # back=True → eng pastda «⬅️ Ortga» (obuna paneliga qaytaradi).
            reply_markup=premium_tariffs_kb(prices, back=True),
        )
    await call.answer("💎 Premium obuna")


@router.callback_query(F.data == "backsub")
async def back_to_subscription(call: CallbackQuery, bot: Bot):
    """«⬅️ Ortga» — premium taklifidan majburiy obuna paneliga qaytish."""
    missing = await subscription_gate(bot, call.from_user.id)
    if not missing:
        # Kutayotganda obuna bo'lib qo'ygan (yoki premium olgan) — to'siq yo'q.
        with contextlib.suppress(TelegramBadRequest):
            await call.message.delete()
        await call.message.answer(
            texts.welcome(call.from_user.full_name), reply_markup=user_menu()
        )
        await call.answer()
        return

    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.SUBSCRIPTION_PANEL, reply_markup=subscription_kb(missing)
        )
    await call.answer("↩️ Ortga")


@router.callback_query(F.data == "noop")
async def noop(call: CallbackQuery):
    """Sahifa ko'rsatkichi «📄 1/3» — bosilganda hech narsa qilmaydi."""
    await call.answer()
