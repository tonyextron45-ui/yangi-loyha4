"""⚙️ Sozlamalar — to'lov kartalari, premium narxlari, yordam limiti
   + balans to'ldirish so'rovlarini tasdiqlash/rad etish."""

from __future__ import annotations

import contextlib
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import (
    BTN_SETTINGS,
    back_settings_kb,
    cancel_kb,
    card_actions_kb,
    cards_manage_kb,
    confirm_card_delete_kb,
    help_limit_kb,
    main_menu,
    referral_setting_kb,
    settings_menu_kb,
    tariffs_kb,
)
from keyboards.user_kb import premium_offer_kb
from states.admin_states import CardSG, RejectSG, SettingsSG
from utils import texts
from utils.filters import HasPerm, IsAdmin
from utils.helpers import safe_send, subscription_gate

log = logging.getLogger(__name__)
router = Router(name="admin:settings")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


# ═══════════════════════════════════════════════════════
#                    SOZLAMALAR MENYUSI
# ═══════════════════════════════════════════════════════

@router.message(F.text == BTN_SETTINGS)
async def settings_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(texts.SETTINGS_MENU, reply_markup=settings_menu_kb())


@router.callback_query(F.data == "set:back")
async def back_settings(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.SETTINGS_MENU, reply_markup=settings_menu_kb())
    await call.answer()


# ═══════════════════════════════════════════════════════
#                   💳 TO'LOV KARTALARI
# ═══════════════════════════════════════════════════════

async def _show_cards(call: CallbackQuery) -> None:
    cards = await q.get_cards()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.cards_panel(cards), reply_markup=cards_manage_kb(cards))


@router.callback_query(F.data == "set:cards")
async def cards_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await _show_cards(call)
    await call.answer()


@router.callback_query(F.data == "card:add", HasPerm("channels"))
async def card_add(call: CallbackQuery, state: FSMContext):
    await state.set_state(CardSG.number)
    await state.update_data(edit_id=None)
    await call.message.answer(texts.ASK_CARD_NUMBER, reply_markup=cancel_kb())
    await call.answer()


@router.callback_query(F.data.startswith("card:edit:"), HasPerm("channels"))
async def card_edit(call: CallbackQuery, state: FSMContext):
    cid = int(call.data.split(":")[2])
    await state.set_state(CardSG.number)
    await state.update_data(edit_id=cid)
    await call.message.answer(texts.ASK_CARD_NUMBER, reply_markup=cancel_kb())
    await call.answer()


@router.message(CardSG.number, F.text)
async def card_number(message: Message, state: FSMContext):
    await state.update_data(number=message.text.strip()[:64])
    await state.set_state(CardSG.holder)
    await message.answer(texts.ASK_CARD_HOLDER, reply_markup=cancel_kb())


@router.message(CardSG.holder, F.text)
async def card_holder(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    number = data["number"]
    holder = message.text.strip()[:64]
    if data.get("edit_id"):
        await q.update_card(data["edit_id"], number, holder)
        await message.answer(texts.CARD_UPDATED, reply_markup=back_settings_kb())
    else:
        await q.add_card(number, holder)
        await message.answer(texts.CARD_ADDED, reply_markup=back_settings_kb())


@router.callback_query(F.data.regexp(r"^card:\d+$"))
async def card_card(call: CallbackQuery):
    cid = int(call.data.split(":")[1])
    card = await q.get_card(cid)
    if card is None:
        await call.answer(texts.CARDS_EMPTY, show_alert=True)
        await _show_cards(call)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.cards_panel([card]), reply_markup=card_actions_kb(cid)
        )
    await call.answer()


@router.callback_query(F.data.startswith("card:del:"), HasPerm("channels"))
async def card_delete_confirm(call: CallbackQuery):
    cid = int(call.data.split(":")[2])
    card = await q.get_card(cid)
    if card is None:
        await call.answer(texts.CARDS_EMPTY, show_alert=True)
        await _show_cards(call)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.confirm_card_delete(card["number"], card["holder"]),
            reply_markup=confirm_card_delete_kb(cid),
        )
    await call.answer()


@router.callback_query(F.data.startswith("card:delyes:"), HasPerm("channels"))
async def card_delete(call: CallbackQuery):
    cid = int(call.data.split(":")[2])
    await q.delete_card(cid)
    await call.answer(texts.CARD_DELETED, show_alert=True)
    await _show_cards(call)


# ═══════════════════════════════════════════════════════
#                  💎 PREMIUM NARXLARI
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "set:tariffs")
async def tariffs_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.tariffs_panel(q.tariff_prices()), reply_markup=tariffs_kb()
        )
    await call.answer()


@router.callback_query(F.data.startswith("tar:"), HasPerm("channels"))
async def tariff_set(call: CallbackQuery, state: FSMContext):
    tariff = call.data.split(":")[1]
    if tariff not in q.TARIFF_DAYS:
        await call.answer()
        return
    await state.set_state(SettingsSG.tariff)
    await state.update_data(tariff=tariff)
    await call.message.answer(
        texts.ask_tariff_price(q.TARIFF_LABEL[tariff]), reply_markup=cancel_kb()
    )
    await call.answer()


@router.message(SettingsSG.tariff, F.text)
async def tariff_save(message: Message, state: FSMContext):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or int(raw) < 0:
        await message.answer(texts.NOT_A_PRICE)
        return
    data = await state.get_data()
    await state.clear()
    await q.set_setting(f"tariff_{data['tariff']}", str(int(raw)))
    await message.answer(texts.TARIFF_UPDATED, reply_markup=back_settings_kb())


# ═══════════════════════════════════════════════════════
#                    🆘 YORDAM LIMITI
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "set:help")
async def help_limit_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.help_limit_panel(q.help_limit()), reply_markup=help_limit_kb()
        )
    await call.answer()


@router.callback_query(F.data == "set:help_edit", HasPerm("channels"))
async def help_limit_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsSG.help_limit)
    await call.message.answer(texts.ASK_HELP_LIMIT, reply_markup=cancel_kb())
    await call.answer()


@router.message(SettingsSG.help_limit, F.text)
async def help_limit_save(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.NOT_A_PRICE)
        return
    await state.clear()
    await q.set_setting("help_limit", str(int(raw)))
    await message.answer(texts.HELP_LIMIT_UPDATED, reply_markup=back_settings_kb())


# ═══════════════════════════════════════════════════════
#                    👥 REFERAL NARXI
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "set:ref")
async def referral_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.referral_settings_panel(q.referral_price()),
            reply_markup=referral_setting_kb(),
        )
    await call.answer()


@router.callback_query(F.data == "set:ref_edit", HasPerm("channels"))
async def referral_ask(call: CallbackQuery, state: FSMContext):
    await state.set_state(SettingsSG.referral)
    await call.message.answer(texts.ASK_REFERRAL_PRICE, reply_markup=cancel_kb())
    await call.answer()


@router.message(SettingsSG.referral, F.text)
async def referral_save(message: Message, state: FSMContext):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or int(raw) < 0:
        await message.answer(texts.NOT_A_PRICE)
        return
    await state.clear()
    await q.set_setting("referral_price", str(int(raw)))
    await message.answer(texts.REFERRAL_PRICE_UPDATED, reply_markup=back_settings_kb())


# ═══════════════════════════════════════════════════════
#          💳 BALANS TO'LDIRISH — TASDIQLASH / RAD ETISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("pay:ok:"))
async def payment_approve(call: CallbackQuery, bot: Bot):
    pid = int(call.data.split(":")[2])
    result = await q.approve_payment(pid, call.from_user.id)
    if result is None:
        await call.answer(texts.PAYMENT_ALREADY_HANDLED, show_alert=True)
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_reply_markup(reply_markup=None)
        return

    uid = result["user_id"]
    balance = await q.add_balance(uid, result["amount"])
    # Majburiy obuna to'sig'ida turgan bo'lsa — «💎 Premium obuna olish» tugmasi
    # bilan yuboramiz, aks holda u premium panelga qayta yo'l topa olmasdi.
    kb = premium_offer_kb() if await subscription_gate(bot, uid) else None
    await safe_send(
        bot, uid, texts.payment_approved_user(result["amount"], balance), reply_markup=kb
    )
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_reply_markup(reply_markup=None)
    await call.answer(texts.PAYMENT_APPROVED_ADMIN, show_alert=True)


@router.callback_query(F.data.startswith("pay:no:"))
async def payment_reject_ask(call: CallbackQuery, state: FSMContext):
    pid = int(call.data.split(":")[2])
    payment = await q.get_payment(pid)
    if payment is None or payment["status"] != "pending":
        await call.answer(texts.PAYMENT_ALREADY_HANDLED, show_alert=True)
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_reply_markup(reply_markup=None)
        return

    await state.set_state(RejectSG.reason)
    await state.update_data(
        pid=pid, chat_id=call.message.chat.id, msg_id=call.message.message_id
    )
    await call.message.answer(texts.ASK_REJECT_REASON, reply_markup=cancel_kb())
    await call.answer()


@router.message(RejectSG.reason, F.text)
async def payment_reject_reason(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    await state.clear()
    reason = message.text.strip()

    result = await q.reject_payment(data["pid"], message.from_user.id, reason)
    if result is None:
        await message.answer(texts.PAYMENT_ALREADY_HANDLED, reply_markup=main_menu())
        return

    await safe_send(
        bot, result["user_id"], texts.payment_rejected_user(result["amount"], reason)
    )
    # Chek ostidagi tugmalarni o'chiramiz.
    with contextlib.suppress(TelegramBadRequest):
        await bot.edit_message_reply_markup(
            chat_id=data["chat_id"], message_id=data["msg_id"], reply_markup=None
        )
    await message.answer(texts.PAYMENT_REJECTED_ADMIN, reply_markup=main_menu())
