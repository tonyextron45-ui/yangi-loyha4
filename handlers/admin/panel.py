"""/admin — parol bilan kirish, asosiy menyu, umumiy «Bekor qilish»."""

from __future__ import annotations

import time

from aiogram import F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database import queries as q
from keyboards.admin_kb import cancel_kb, main_menu
from states.admin_states import AuthSG
from utils import texts
from utils.helpers import full_time

router = Router(name="admin:panel")

# Brute-force himoyasi: telegram_id → [urinishlar, blok tugash vaqti]
_tries: dict[int, int] = {}
_locked: dict[int, float] = {}


def _is_locked(tid: int) -> int:
    """Qolgan blok daqiqalari (0 → bloklanmagan)."""
    until = _locked.get(tid)
    if until is None:
        return 0
    left = until - time.monotonic()
    if left <= 0:
        _locked.pop(tid, None)
        _tries.pop(tid, None)
        return 0
    return max(1, int(left // 60) + 1)


@router.message(Command("admin"))
async def admin_entry(message: Message, state: FSMContext):
    tid = message.from_user.id

    # Admin bo'lmaganga panel haqida hech narsa bildirilmaydi (TZ §8.1).
    if not q.is_admin(tid):
        await message.answer(texts.UNKNOWN_COMMAND)
        return

    locked = _is_locked(tid)
    if locked:
        await message.answer(texts.password_locked(locked))
        return

    await state.set_state(AuthSG.password)
    await message.answer(texts.ASK_PASSWORD, reply_markup=cancel_kb())


@router.message(AuthSG.password, F.text)
async def check_password(message: Message, state: FSMContext):
    tid = message.from_user.id

    locked = _is_locked(tid)
    if locked:
        await state.clear()
        await message.answer(texts.password_locked(locked))
        return

    # Parolni xabar sifatida qoldirmaymiz — chat toza va xavfsiz qoladi.
    try:
        await message.delete()
    except Exception:
        pass

    if message.text.strip() != config.admin_password:
        _tries[tid] = _tries.get(tid, 0) + 1
        if _tries[tid] >= config.max_password_tries:
            _locked[tid] = time.monotonic() + config.password_lock_minutes * 60
            _tries.pop(tid, None)
            await state.clear()
            await message.answer(texts.password_locked(config.password_lock_minutes))
            return
        left = config.max_password_tries - _tries[tid]
        await message.answer(f"{texts.WRONG_PASSWORD}\n<i>Qolgan urinish: {left}</i>")
        return

    _tries.pop(tid, None)
    await state.clear()
    await _show_panel(message)


async def _show_panel(message: Message) -> None:
    admin = q.get_admin(message.from_user.id)
    role = admin["role"] if admin else "helper"
    await message.answer(
        texts.admin_panel(message.from_user.full_name, role, full_time()),
        reply_markup=main_menu(),
    )


# ═══════════════════════════════════════════════════════
#             UMUMIY «BEKOR QILISH» (barcha FSM)
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer(texts.CANCELLED)
    try:
        await call.message.delete()
    except Exception:
        await call.message.edit_reply_markup(reply_markup=None)
    await call.message.answer(texts.CANCELLED, reply_markup=main_menu())


@router.message(Command("cancel"), StateFilter("*"))
async def cancel_cmd(message: Message, state: FSMContext):
    if not q.is_admin(message.from_user.id):
        return
    await state.clear()
    await message.answer(texts.CANCELLED, reply_markup=main_menu())
