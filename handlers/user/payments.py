"""💳 Balans to'ldirish — summa kiritish + chek (rasm/PDF) yuborish → adminga.

OQIM
────
  ① «💳 Balansni to'ldirish» yoki pullik kontent «🛒 Sotib olish» (balans kam)
  ② Karta ma'lumotlari ko'rsatiladi, summa so'raladi
  ③ Chek (rasm yoki PDF) yuboriladi
  ④ So'rov barcha adminlarga «✅ Tasdiqlash / ❌ Rad etish» tugmalari bilan boradi
"""

from __future__ import annotations

import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from database import queries as q
from keyboards.admin_kb import payment_action_kb
from keyboards.user_kb import user_cancel_kb
from states.admin_states import TopUpSG
from utils import texts
from utils.helpers import fire_and_forget, full_time

log = logging.getLogger(__name__)
router = Router(name="user:payments")


async def open_topup(bot: Bot, chat_id: int, state: FSMContext) -> None:
    """Hisob to'ldirish bo'limini ochadi (karta ma'lumotlari + summa so'rovi)."""
    cards = await q.get_cards()
    if not cards:
        await state.clear()
        await bot.send_message(chat_id, texts.NO_CARDS)
        return
    await state.set_state(TopUpSG.amount)
    await bot.send_message(chat_id, texts.topup_intro(cards), reply_markup=user_cancel_kb())


@router.message(TopUpSG.amount, F.text)
async def got_amount(message: Message, state: FSMContext):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.NOT_AN_AMOUNT)
        return
    await state.update_data(amount=int(raw))
    await state.set_state(TopUpSG.receipt)
    await message.answer(texts.ASK_RECEIPT, reply_markup=user_cancel_kb())


@router.message(TopUpSG.amount)
async def amount_invalid(message: Message):
    await message.answer(texts.NOT_AN_AMOUNT)


@router.message(TopUpSG.receipt, F.photo | F.document)
async def got_receipt(message: Message, state: FSMContext, bot: Bot):
    if message.photo:
        rtype, fid = "photo", message.photo[-1].file_id
    else:
        rtype, fid = "document", message.document.file_id

    data = await state.get_data()
    amount = int(data["amount"])
    await state.clear()

    pid = await q.create_payment(message.from_user.id, amount, fid, rtype)

    user = message.from_user
    caption = texts.payment_request_admin(
        user.full_name, user.username, user.id, amount, full_time()
    )
    # Adminlarga fon rejimida yuboramiz — foydalanuvchi kutib turmasin.
    fire_and_forget(_notify_payment_admins(bot, pid, rtype, fid, caption))

    await message.answer(texts.topup_submitted(amount))


@router.message(TopUpSG.receipt)
async def receipt_invalid(message: Message):
    await message.answer(texts.NEED_RECEIPT, reply_markup=user_cancel_kb())


async def _notify_payment_admins(bot: Bot, pid: int, rtype: str, fid: str, caption: str) -> None:
    kb = payment_action_kb(pid)
    for admin in q.all_admins():
        tid = admin["telegram_id"]
        try:
            if rtype == "photo":
                await bot.send_photo(tid, fid, caption=caption, reply_markup=kb)
            else:
                await bot.send_document(tid, fid, caption=caption, reply_markup=kb)
        except TelegramAPIError:
            log.warning("To'lov cheki adminga yuborilmadi: %s", tid)
