"""🔔 Bildirishnoma yoqish/o'chirish."""

from __future__ import annotations

import contextlib

from aiogram import F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import BTN_NOTIFY, notify_kb
from utils import texts
from utils.filters import IsAdmin

router = Router(name="admin:notifications")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == BTN_NOTIFY)
async def notify_panel(message: Message, state: FSMContext):
    await state.clear()
    is_on = q.notifications_on()
    await message.answer(texts.notifications_panel(is_on), reply_markup=notify_kb(is_on))


@router.callback_query(F.data == "nt:toggle")
async def toggle(call: CallbackQuery):
    is_on = await q.toggle_notifications()
    await call.answer("🔔 Yoqildi!" if is_on else "🔕 O'chirildi!")
    # Holat real vaqtda o'zgaradi — xabar qayta yuborilmaydi.
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.notifications_panel(is_on), reply_markup=notify_kb(is_on)
        )
