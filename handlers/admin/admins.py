"""👑 Adminlar va huquqlar tizimi."""

from __future__ import annotations

import contextlib

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import (
    BTN_ADMINS,
    admin_card_kb,
    admin_list_kb,
    admin_menu_kb,
    back_admin_kb,
    cancel_kb,
    confirm_admin_kb,
)
from states.admin_states import AdminSG
from utils import texts
from utils.filters import HasPerm, IsAdmin
from utils.helpers import safe_send

router = Router(name="admin:admins")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


@router.message(F.text == BTN_ADMINS)
async def admin_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        texts.ADMIN_MENU,
        reply_markup=admin_menu_kb(q.has_perm(message.from_user.id, "admins")),
    )


@router.callback_query(F.data == "a:back")
async def back_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.ADMIN_MENU,
            reply_markup=admin_menu_kb(q.has_perm(call.from_user.id, "admins")),
        )
    await call.answer()


# ═══════════════════════════════════════════════════════
#                    ➕ ADMIN QO'SHISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "a:add", HasPerm("admins"))
async def ask_admin_id(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdminSG.new_id)
    await call.message.answer(texts.ASK_ADMIN_ID, reply_markup=cancel_kb())
    await call.answer()


@router.message(AdminSG.new_id, F.text)
async def add_admin(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    if not raw.lstrip("-").isdigit():
        await message.answer("⚠️ Faqat raqam kiriting! <i>(masalan: 123456789)</i>")
        return

    tid = int(raw)
    if q.is_admin(tid):
        await message.answer(texts.ADMIN_ALREADY)
        return

    # Faqat botni ishga tushirgan foydalanuvchini admin qilish mumkin.
    if await q.get_user(tid) is None:
        await message.answer(texts.ADMIN_USER_NOT_FOUND)
        return

    await state.clear()
    await q.add_admin(tid)
    await safe_send(bot, tid, texts.NEW_ADMIN_GREETING)
    await message.answer(texts.ADMIN_ADDED, reply_markup=back_admin_kb())


# ═══════════════════════════════════════════════════════
#                 👥 ADMINLAR RO'YXATI
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "a:list")
async def admin_list(call: CallbackQuery):
    admins = q.all_admins()
    if not admins:
        await call.answer(texts.ADMINS_EMPTY, show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            f"👥 <b>ADMINLAR</b>\n\n📋 Jami: <b>{len(admins)}</b> ta\n\n"
            "<i>Ma'lumot uchun ID ni bosing 👇</i>",
            reply_markup=admin_list_kb(admins, "adm"),
        )
    await call.answer()


@router.callback_query(F.data.startswith("adm:"))
async def admin_card(call: CallbackQuery):
    tid = int(call.data.split(":")[1])
    admin = q.get_admin(tid)
    if admin is None:
        await call.answer("❌ Admin topilmadi!", show_alert=True)
        return

    user = await q.get_user(tid)
    # Toggle tugmalari faqat asosiy adminga ko'rinadi (TZ §8.6.2).
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.admin_card(admin, user["username"] if user else None),
            reply_markup=admin_card_kb(admin, q.is_main_admin(call.from_user.id)),
        )
    await call.answer()


# ═══════════════════════════════════════════════════════
#                  🔐 HUQUQ TOGGLE
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("perm:"))
async def toggle_perm(call: CallbackQuery, bot: Bot):
    if not q.is_main_admin(call.from_user.id):
        await call.answer("⛔️ Huquqlarni faqat asosiy admin boshqaradi!", show_alert=True)
        return

    _, raw_tid, perm = call.data.split(":")
    tid = int(raw_tid)
    admin = q.get_admin(tid)
    if admin is None:
        await call.answer("❌ Admin topilmadi!", show_alert=True)
        return
    if admin["role"] == "main":
        await call.answer("👑 Asosiy adminda barcha huquqlar doim bor!", show_alert=True)
        return

    granted = await q.toggle_perm(tid, perm)
    await call.answer(("✅ Huquq berildi" if granted else "❌ Huquq olindi"))

    # O'sha adminga xabar boradi.
    await safe_send(bot, tid, texts.perm_granted(perm) if granted else texts.perm_revoked(perm))

    # Karta real vaqtda edit bo'ladi.
    updated = q.get_admin(tid)
    user = await q.get_user(tid)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.admin_card(updated, user["username"] if user else None),
            reply_markup=admin_card_kb(updated, True),
        )


# ═══════════════════════════════════════════════════════
#                   🗑 ADMIN O'CHIRISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "a:del", HasPerm("admins"))
async def delete_list(call: CallbackQuery):
    admins = q.all_admins()
    if not admins:
        await call.answer(texts.ADMINS_EMPTY, show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            "🗑 <b>ADMIN O'CHIRISH</b>\n\n<i>O'chirmoqchi bo'lganingizni tanlang 👇</i>",
            reply_markup=admin_list_kb(admins, "adel"),
        )
    await call.answer()


@router.callback_query(F.data.startswith("adel:"), HasPerm("admins"))
async def confirm_delete(call: CallbackQuery):
    tid = int(call.data.split(":")[1])

    if q.is_main_admin(tid):
        await call.answer(texts.CANNOT_DELETE_MAIN, show_alert=True)
        return
    if tid == call.from_user.id:
        await call.answer(texts.CANNOT_DELETE_SELF, show_alert=True)
        return

    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.confirm_admin_delete(tid), reply_markup=confirm_admin_kb(tid)
        )
    await call.answer()


@router.callback_query(F.data.startswith("ayes:"), HasPerm("admins"))
async def do_delete(call: CallbackQuery, bot: Bot):
    tid = int(call.data.split(":")[1])

    if q.is_main_admin(tid):
        await call.answer(texts.CANNOT_DELETE_MAIN, show_alert=True)
        return
    if tid == call.from_user.id:
        await call.answer(texts.CANNOT_DELETE_SELF, show_alert=True)
        return

    await q.remove_admin(tid)
    await safe_send(bot, tid, texts.ADMIN_REMOVED_NOTICE)
    await call.answer("✅ O'chirildi!")
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.ADMIN_DELETED, reply_markup=back_admin_kb())


@router.callback_query(F.data == "ano")
async def cancel_delete(call: CallbackQuery):
    await call.answer(texts.CANCELLED)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.CANCELLED, reply_markup=back_admin_kb())
