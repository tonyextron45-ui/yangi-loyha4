"""📊 Statistika + foydalanuvchilar boshqaruvi (izlash, balans) + ⛔️ bloklash."""

from __future__ import annotations

import contextlib
import time

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database import queries as q
from keyboards.admin_kb import (
    BTN_STATS,
    cancel_kb,
    scan_confirm_kb,
    scan_done_kb,
    stats_kb,
    user_card_kb,
    users_kb,
)
from states.admin_states import BalanceSG, BanSG, UserSearchSG
from utils import texts
from utils.broadcaster import ScanResult, scan_inactive
from utils.filters import IsAdmin
from utils.helpers import fmt_date, fmt_elapsed, fmt_left, hhmm, safe_send, status_line

router = Router(name="admin:statistics")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _stats_text() -> str:
    return texts.bot_stats(await q.user_stats(), hhmm())


def _card_text(user: dict) -> str:
    """Foydalanuvchi kartasi — balans va premium holati bilan."""
    if q.premium_active(user):
        tariff = q.TARIFF_LABEL.get(user.get("premium_tariff"), "—")
        left = fmt_left(user["premium_until"] - int(time.time()))
        premium_line = f"💎 Premium: 🟢 <b>{tariff}</b> <i>({left} qoldi)</i>"
    else:
        premium_line = "💎 Premium: —"
    return texts.user_card(user, fmt_date(user["joined_at"]), status_line(user), premium_line)


@router.message(F.text == BTN_STATS)
async def show_stats(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(await _stats_text(), reply_markup=stats_kb())


@router.callback_query(F.data.in_({"st:refresh", "st:back"}))
async def refresh_stats(call: CallbackQuery):
    """Xabar edit qilinadi — qayta yuborilmaydi (TZ §13.5)."""
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(await _stats_text(), reply_markup=stats_kb())
    await call.answer("🔄 Yangilandi" if call.data == "st:refresh" else None)


# ═══════════════════════════════════════════════════════
#        🔍 NOFAOL AKKAUNTLARNI TEKSHIRISH (SKANER)
# ═══════════════════════════════════════════════════════
# Telegram akkaunti o'chirilgan foydalanuvchilar hech qanday hodisa yubormaydi —
# ularni faqat «so'rab» aniqlash mumkin. Shu bois bu alohida, qo'lda ishga
# tushiriladigan amal: bir vaqtda FAQAT bittasi ishlaydi.

_scan_running = False


@router.callback_query(F.data == "st:scan")
async def ask_scan(call: CallbackQuery):
    if _scan_running:
        await call.answer(texts.SCAN_RUNNING, show_alert=True)
        return

    total = await q.users_total()
    if not total:
        await call.answer(texts.SCAN_NO_USERS, show_alert=True)
        return

    eta = fmt_elapsed(total / max(1, config.broadcast_rate))
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.scan_intro(total, eta), reply_markup=scan_confirm_kb()
        )
    await call.answer()


@router.callback_query(F.data == "st:scango")
async def run_scan(call: CallbackQuery, bot: Bot):
    global _scan_running
    if _scan_running:
        await call.answer(texts.SCAN_RUNNING, show_alert=True)
        return

    _scan_running = True
    await call.answer("🔍 Tekshiruv boshlandi!")
    msg = call.message

    async def on_progress(r: ScanResult) -> None:
        # Hisobot 3 sekundda bir marta yangilanadi (broadcaster'da) — Telegram
        # limitiga urilmaydi. «message is not modified» xatosi zararsiz.
        with contextlib.suppress(TelegramBadRequest):
            await msg.edit_text(texts.scan_progress(r.checked, r.total, r.deleted, r.blocked))

    with contextlib.suppress(TelegramBadRequest):
        await msg.edit_text(texts.scan_progress(0, await q.users_total(), 0, 0))

    try:
        result, elapsed = await scan_inactive(bot, on_progress)
    finally:
        _scan_running = False

    with contextlib.suppress(TelegramBadRequest):
        await msg.edit_text(
            texts.scan_done(
                result.checked, result.deleted, result.blocked,
                result.revived, fmt_elapsed(elapsed),
            ),
            reply_markup=scan_done_kb(),
        )


# ═══════════════════════════════════════════════════════
#              👥 FOYDALANUVCHILAR RO'YXATI
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("upg:"))
async def users_list(call: CallbackQuery):
    page = int(call.data.split(":")[1])
    total = await q.users_total()
    if not total:
        await call.answer(texts.USERS_EMPTY, show_alert=True)
        return

    pages = max(1, -(-total // config.users_per_page))
    if page < 1:
        await call.answer("⚠️ Bu birinchi sahifa!", show_alert=True)
        return
    if page > pages:
        await call.answer("⚠️ Bu oxirgi sahifa!", show_alert=True)
        return

    ids = await q.users_page((page - 1) * config.users_per_page, config.users_per_page)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            f"👥 <b>FOYDALANUVCHILAR</b>\n\n"
            f"📋 Jami: <b>{texts.num(total)}</b> ta\n"
            f"📄 Sahifa: <b>{page}/{pages}</b>\n\n"
            f"<i>Ma'lumot uchun ID ni bosing 👇</i>",
            reply_markup=users_kb(ids, page, total),
        )
    await call.answer()


async def _show_card(call: CallbackQuery, tid: int, page: int = 1) -> None:
    user = await q.get_user(tid)
    if user is None:
        await call.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            _card_text(user), reply_markup=user_card_kb(user, page)
        )


@router.callback_query(F.data.startswith("usr:"))
async def user_card(call: CallbackQuery):
    await _show_card(call, int(call.data.split(":")[1]))
    await call.answer()


# ═══════════════════════════════════════════════════════
#              🔍 ID ORQALI IZLASH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "usrfind")
async def ask_user_search(call: CallbackQuery, state: FSMContext):
    await state.set_state(UserSearchSG.query)
    await call.message.answer(texts.ASK_USER_ID_SEARCH, reply_markup=cancel_kb())
    await call.answer()


@router.message(UserSearchSG.query, F.text)
async def user_search(message: Message, state: FSMContext):
    raw = message.text.strip().lstrip("@")
    if not raw.isdigit():
        await message.answer(texts.ASK_ONLY_NUMBER, reply_markup=cancel_kb())
        return
    user = await q.get_user(int(raw))
    if user is None:
        # Holat saqlanadi — admin boshqa ID kiritishi mumkin.
        await message.answer(texts.USER_SEARCH_NOT_FOUND, reply_markup=cancel_kb())
        return
    await state.clear()
    await message.answer(_card_text(user), reply_markup=user_card_kb(user))


# ═══════════════════════════════════════════════════════
#            💰 BALANS QO'SHISH / AYIRISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ubal:"))
async def ask_balance_change(call: CallbackQuery, state: FSMContext):
    _, op, raw = call.data.split(":")
    tid = int(raw)
    if await q.get_user(tid) is None:
        await call.answer("❌ Foydalanuvchi topilmadi!", show_alert=True)
        return
    await state.set_state(BalanceSG.amount)
    await state.update_data(target=tid, op=op)
    await call.message.answer(texts.ask_balance_amount(op, tid), reply_markup=cancel_kb())
    await call.answer()


@router.message(BalanceSG.amount, F.text)
async def do_balance_change(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.NOT_A_PRICE, reply_markup=cancel_kb())
        return

    amount = int(raw)
    data = await state.get_data()
    tid, op = data["target"], data["op"]
    await state.clear()

    if op == "add":
        balance = await q.add_balance(tid, amount)
        await safe_send(bot, tid, texts.balance_added_notice(amount, balance))
        note = texts.balance_admin_added(tid, amount, balance)
    else:
        if not await q.deduct_balance(tid, amount):
            balance = await q.get_balance(tid)
            user = await q.get_user(tid)
            await message.answer(
                texts.balance_admin_insufficient(tid, balance) + "\n\n" + _card_text(user),
                reply_markup=user_card_kb(user),
            )
            return
        balance = await q.get_balance(tid)
        await safe_send(bot, tid, texts.balance_deducted_notice(amount, balance))
        note = texts.balance_admin_deducted(tid, amount, balance)

    user = await q.get_user(tid)
    await message.answer(note + "\n\n" + _card_text(user), reply_markup=user_card_kb(user))


# ═══════════════════════════════════════════════════════
#                   ⛔️ BLOKLASH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ublock:"))
async def ask_ban(call: CallbackQuery, state: FSMContext):
    tid = int(call.data.split(":")[1])
    if q.is_admin(tid):
        await call.answer("⛔️ Adminni bloklab bo'lmaydi!", show_alert=True)
        return

    await state.set_state(BanSG.minutes)
    await state.update_data(target=tid)
    await call.message.answer(texts.ASK_BAN_MINUTES, reply_markup=cancel_kb())
    await call.answer()


@router.message(BanSG.minutes, F.text)
async def do_ban(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.NOT_A_MINUTE)
        return

    minutes = int(raw)
    data = await state.get_data()
    tid = data["target"]
    await state.clear()

    await q.ban_user(tid, minutes)
    await safe_send(bot, tid, texts.banned_notice(minutes))

    user = await q.get_user(tid)
    await message.answer(
        f"⛔️ <code>{tid}</code> <b>{minutes} daqiqaga</b> bloklandi!\n\n"
        + _card_text(user),
        reply_markup=user_card_kb(user),
    )


@router.callback_query(F.data.startswith("uunblock:"))
async def do_unban(call: CallbackQuery, bot: Bot):
    tid = int(call.data.split(":")[1])
    await q.unban_user(tid)
    await safe_send(bot, tid, texts.UNBANNED_BY_ADMIN)
    await call.answer("🔓 Blokdan chiqarildi!")
    # Karta real vaqtda yangilanadi — tugma ham «⛔️ Bloklash» ga o'zgaradi.
    await _show_card(call, tid)
