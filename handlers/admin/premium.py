"""💎 Premium obunachilar — admin ko'rish, muddat real vaqtda, bekor qilish."""

from __future__ import annotations

import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import (
    BTN_PREMIUM,
    confirm_cancel_premium_kb,
    premium_sub_card_kb,
    premium_subs_kb,
)
from utils import texts
from utils.filters import IsAdmin
from utils.helpers import fmt_date, fmt_left, safe_send

router = Router(name="admin:premium")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


def _now() -> int:
    return int(time.time())


async def _show_list(call: CallbackQuery) -> None:
    ids = await q.premium_users()
    with contextlib.suppress(TelegramBadRequest):
        if not ids:
            await call.message.edit_text(texts.PREMIUM_SUBS_EMPTY)
        else:
            await call.message.edit_text(
                texts.premium_subs_header(len(ids)), reply_markup=premium_subs_kb(ids)
            )


@router.message(F.text == BTN_PREMIUM)
async def premium_subs_menu(message: Message, state: FSMContext):
    await state.clear()
    ids = await q.premium_users()
    if not ids:
        await message.answer(texts.PREMIUM_SUBS_EMPTY)
        return
    await message.answer(texts.premium_subs_header(len(ids)), reply_markup=premium_subs_kb(ids))


@router.callback_query(F.data == "psubs")
async def refresh_list(call: CallbackQuery):
    await _show_list(call)
    await call.answer()


@router.callback_query(F.data.startswith("psub:"))
async def sub_card(call: CallbackQuery):
    tid = int(call.data.split(":")[1])
    user = await q.get_user(tid)
    if user is None or not q.premium_active(user):
        await call.answer("❌ Obunachi topilmadi yoki muddati tugagan!", show_alert=True)
        await _show_list(call)
        return

    tariff = q.TARIFF_LABEL.get(user["premium_tariff"], "—")
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.premium_sub_card(
                user["full_name"], user["username"], tid, tariff,
                fmt_date(user["premium_until"]), fmt_left(user["premium_until"] - _now()),
            ),
            reply_markup=premium_sub_card_kb(tid),
        )
    await call.answer()


@router.callback_query(F.data.startswith("pcancel:"))
async def cancel_confirm(call: CallbackQuery):
    tid = int(call.data.split(":")[1])
    user = await q.get_user(tid)
    name = user["full_name"] if user else str(tid)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.confirm_cancel_premium(name), reply_markup=confirm_cancel_premium_kb(tid)
        )
    await call.answer()


@router.callback_query(F.data.startswith("pcyes:"))
async def do_cancel(call: CallbackQuery, bot: Bot):
    tid = int(call.data.split(":")[1])
    await q.cancel_premium(tid)
    await safe_send(bot, tid, texts.premium_cancelled_notice())
    await call.answer(texts.PREMIUM_CANCELLED_ADMIN, show_alert=True)
    await _show_list(call)
