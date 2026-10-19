"""💰 Balans · 💎 Premium obuna · 🆘 Yordam — foydalanuvchi pastki menyusi.

Pastki menyu tugmalari (F.text == BTN...) HAR QANDAY holatda ishlaydi va joriy
jarayondan (topup/help) chiqib ketadi — shu bois ular content router'idagi
umumiy «raqam emas» to'sig'idan OLDIN ulanadi.
"""

from __future__ import annotations

import contextlib
import logging
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from handlers.user.payments import open_topup
from keyboards.user_kb import (
    BTN_BALANCE,
    BTN_HELP,
    BTN_PREMIUM,
    BTN_REFERRAL,
    premium_confirm_kb,
    premium_tariffs_kb,
    referral_kb,
    topup_button_kb,
    user_cancel_kb,
    user_menu,
)
from states.admin_states import HelpSG
from utils import texts
from utils.helpers import (
    fire_and_forget,
    fmt_date,
    fmt_left,
    reward_referrer,
    safe_send,
    subscription_gate,
)

log = logging.getLogger(__name__)
router = Router(name="user:menu")


def _now() -> int:
    return int(time.time())


def _premium_left(user: dict | None) -> str | None:
    if not q.premium_active(user):
        return None
    return fmt_left(user["premium_until"] - _now())


# ═══════════════════════════════════════════════════════
#                       💰 BALANS
# ═══════════════════════════════════════════════════════

@router.message(F.text == BTN_BALANCE)
async def balance_menu(message: Message, state: FSMContext):
    await state.clear()
    user = message.from_user
    db_user = await q.get_user(user.id)
    balance = int(db_user["balance"]) if db_user else 0
    await message.answer(
        texts.balance_panel(
            user.full_name, user.username, user.id, balance,
            q.premium_active(db_user), _premium_left(db_user),
        ),
        reply_markup=topup_button_kb(),
    )


@router.callback_query(F.data == "topup")
async def cb_topup(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Hisob to'ldirish — eski context o'chib, yangisi ochiladi."""
    with contextlib.suppress(TelegramBadRequest):
        await call.message.delete()
    await open_topup(bot, call.message.chat.id, state)
    await call.answer()


# ═══════════════════════════════════════════════════════
#                    💎 PREMIUM OBUNA
# ═══════════════════════════════════════════════════════

def _active_panel_text(db_user: dict) -> str:
    """Faol obunachi uchun to'liq ma'lumot kartasi (qayta sotib olish YO'Q)."""
    return texts.premium_active_panel(
        q.TARIFF_LABEL.get(db_user.get("premium_tariff"), "—"),
        fmt_date(db_user.get("premium_started")),
        fmt_date(db_user["premium_until"]),
        fmt_left(db_user["premium_until"] - _now()),
    )


@router.message(F.text == BTN_PREMIUM)
async def premium_menu(message: Message, state: FSMContext):
    await state.clear()
    db_user = await q.get_user(message.from_user.id)

    # 💎 Obuna allaqachon faol → tariflar KO'RSATILMAYDI, faqat ma'lumot.
    if q.premium_active(db_user):
        await message.answer(_active_panel_text(db_user))
        return

    prices = q.tariff_prices()
    await message.answer(
        texts.premium_panel(prices), reply_markup=premium_tariffs_kb(prices)
    )


@router.callback_query(F.data.startswith("prem:"))
async def premium_choose(call: CallbackQuery):
    tariff = call.data.split(":")[1]
    if tariff not in q.TARIFF_DAYS:
        await call.answer()
        return

    # Eski xabardagi tugma bosilsa ham qayta sotib olishga yo'l qo'ymaymiz.
    db_user = await q.get_user(call.from_user.id)
    if q.premium_active(db_user):
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_text(_active_panel_text(db_user))
        await call.answer("💎 Sizda allaqachon faol premium obuna bor!", show_alert=True)
        return

    price = q.tariff_price(tariff)
    balance = await q.get_balance(call.from_user.id)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.premium_confirm(q.TARIFF_LABEL[tariff], price, balance),
            reply_markup=premium_confirm_kb(tariff),
        )
    await call.answer()


@router.callback_query(F.data == "premno")
async def premium_cancel(call: CallbackQuery, bot: Bot):
    db_user = await q.get_user(call.from_user.id)
    if q.premium_active(db_user):
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_text(_active_panel_text(db_user))
        await call.answer("↩️ Bekor qilindi")
        return

    prices = q.tariff_prices()

    # «💎 Obunasiz ko'rish» orqali kelgan bo'lsa — o'sha taklif paneliga qaytamiz
    # («⬅️ Ortga» tugmasi bilan), aks holda foydalanuvchi hech qaerga bora olmasdi.
    if await subscription_gate(bot, call.from_user.id):
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_text(
                texts.premium_gate_panel(prices),
                reply_markup=premium_tariffs_kb(prices, back=True),
            )
        await call.answer("↩️ Bekor qilindi")
        return

    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.premium_panel(prices), reply_markup=premium_tariffs_kb(prices)
        )
    await call.answer("↩️ Bekor qilindi")


@router.callback_query(F.data.startswith("premyes:"))
async def premium_buy(call: CallbackQuery, state: FSMContext, bot: Bot):
    tariff = call.data.split(":")[1]
    if tariff not in q.TARIFF_DAYS:
        await call.answer()
        return

    tid = call.from_user.id

    # Faol obunachi qayta sotib ololmaydi (ikkinchi qatlam himoya).
    db_user = await q.get_user(tid)
    if q.premium_active(db_user):
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_text(_active_panel_text(db_user))
        await call.answer("💎 Sizda allaqachon faol premium obuna bor!", show_alert=True)
        return

    price = q.tariff_price(tariff)
    balance = await q.get_balance(tid)

    # Mablag' yetarli emas → hisob to'ldirish bo'limi (eski context o'chadi).
    if balance < price:
        with contextlib.suppress(TelegramBadRequest):
            await call.message.delete()
        await bot.send_message(call.message.chat.id, texts.premium_insufficient(price, balance))
        await open_topup(bot, call.message.chat.id, state)
        await call.answer()
        return

    # Sotib olishdan OLDIN aniqlaymiz: majburiy obuna to'sig'ida turganmidi?
    # (Keyin premium tufayli to'siq umuman ko'rinmaydi — bilib bo'lmaydi.)
    was_gated = bool(await subscription_gate(bot, tid))

    if not await q.deduct_balance(tid, price):
        await call.answer("❌ Mablag' yetarli emas!", show_alert=True)
        return

    until = await q.grant_premium(tid, tariff)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.premium_congrats(q.TARIFF_LABEL[tariff], fmt_date(until))
        )
    await call.answer("🎉 Tabriklaymiz!")

    # 💎 «Obunasiz ko'rish» yo'li bilan kelgan: endi to'siqdan ozod — uni
    # kutayotgan pastki menyu bilan botga «kiritamiz» va referal mukofotini
    # (bo'lsa) taklif qiluvchiga beramiz.
    if was_gated:
        await reward_referrer(bot, tid)
        await call.message.answer(
            texts.welcome(call.from_user.full_name), reply_markup=user_menu()
        )


# ═══════════════════════════════════════════════════════
#                     👥 REFERAL DASTURI
# ═══════════════════════════════════════════════════════

@router.message(F.text == BTN_REFERRAL)
async def referral_menu(message: Message, state: FSMContext, bot: Bot):
    await state.clear()
    tid = message.from_user.id
    username = (await bot.me()).username or "bot"
    link = f"https://t.me/{username}?start=ref_{tid}"
    count = await q.referral_count(tid)
    earned = await q.referral_earned(tid)
    await message.answer(
        texts.referral_panel(link, q.referral_price(), count, earned),
        reply_markup=referral_kb(link),
    )


# ═══════════════════════════════════════════════════════
#                        🆘 YORDAM
# ═══════════════════════════════════════════════════════

@router.message(F.text == BTN_HELP)
async def help_menu(message: Message, state: FSMContext):
    await state.clear()
    used, ws = await q.help_state(message.from_user.id)
    limit = q.help_limit()
    remaining = max(0, limit - used)
    reset_left = fmt_left(ws + q.HELP_WINDOW - _now()) if used > 0 else None

    if remaining <= 0:
        await message.answer(texts.help_limit_reached(reset_left or "12 soat"))
        return

    await state.set_state(HelpSG.message)
    await message.answer(
        texts.help_panel(remaining, limit, reset_left), reply_markup=user_cancel_kb()
    )


@router.message(HelpSG.message, F.text)
async def help_send(message: Message, state: FSMContext, bot: Bot):
    tid = message.from_user.id
    allowed, remaining, reset_at = await q.help_consume(tid)
    await state.clear()

    if not allowed:
        await message.answer(texts.help_limit_reached(fmt_left(reset_at - _now())))
        return

    user = message.from_user
    header = texts.help_message_admin(user.full_name, user.username, user.id)
    body = f"{header}\n\n{texts.esc(message.text)}"
    fire_and_forget(_notify_help_admins(bot, body))

    await message.answer(texts.help_message_sent(remaining, q.help_limit()))


@router.message(HelpSG.message)
async def help_invalid(message: Message):
    await message.answer(
        "⚠️ Iltimos, xabaringizni <b>matn</b> ko'rinishida yuboring!",
        reply_markup=user_cancel_kb(),
    )


async def _notify_help_admins(bot: Bot, body: str) -> None:
    for admin in q.all_admins():
        await safe_send(bot, admin["telegram_id"], body)


# ═══════════════════════════════════════════════════════
#                  UMUMIY «BEKOR QILISH»
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "ucancel")
async def user_cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.delete()
    await call.answer("↩️ Bekor qilindi")
