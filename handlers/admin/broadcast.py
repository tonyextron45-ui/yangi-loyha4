"""📨 Ommaviy xabar yuborish — barcha turdagi xabarlar, real vaqt hisobot."""

from __future__ import annotations

import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import BTN_BROADCAST, broadcast_confirm_kb, cancel_kb, main_menu
from states.admin_states import BroadcastSG
from utils import texts
from utils.broadcaster import Progress, broadcast
from utils.filters import IsAdmin
from utils.helpers import fmt_elapsed

router = Router(name="admin:broadcast")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == BTN_BROADCAST)
async def ask_message(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(BroadcastSG.message)
    await message.answer(texts.ASK_BROADCAST, reply_markup=cancel_kb())


@router.message(BroadcastSG.message)
async def got_message(message: Message, state: FSMContext):
    """Har qanday tur qabul qilinadi — copy_message hammasini saqlaydi."""
    await state.update_data(from_chat=message.chat.id, msg_id=message.message_id)
    await state.set_state(BroadcastSG.confirm)
    # Preview: adminning o'z xabarini ko'rsatib, ostiga tasdiq tugmasi.
    await message.answer(texts.BROADCAST_PREVIEW, reply_markup=broadcast_confirm_kb())


@router.callback_query(F.data == "bc:yes", BroadcastSG.confirm)
async def do_broadcast(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()

    stats = await q.user_stats()
    if not stats["active"]:
        await call.answer(texts.BROADCAST_NO_USERS, show_alert=True)
        return

    await call.answer("🚀 Boshlandi!")
    status = await call.message.edit_text(texts.broadcast_progress(0, 0, 0))

    async def on_progress(p: Progress) -> None:
        # Telegram bir xil matnli edit'ni rad etadi — shuni yutamiz.
        with contextlib.suppress(TelegramBadRequest):
            await status.edit_text(texts.broadcast_progress(p.sent, p.failed, p.percent))

    result, elapsed = await broadcast(
        bot,
        from_chat_id=data["from_chat"],
        message_id=data["msg_id"],
        on_progress=on_progress,
    )

    with contextlib.suppress(TelegramBadRequest):
        await status.edit_text(
            texts.broadcast_done(
                total=result.total,
                sent=result.sent,
                failed=result.failed,
                elapsed=fmt_elapsed(elapsed),
            )
        )
    await call.message.answer("✅ Yakunlandi!", reply_markup=main_menu())
