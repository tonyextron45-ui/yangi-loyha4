"""📡 Baza / Majburiy / Zayavka kanallar boshqaruvi."""

from __future__ import annotations

import contextlib
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import (
    BTN_CHANNELS,
    add_channel_kb,
    back_channel_kb,
    cancel_kb,
    channel_edit_kb,
    channel_list_kb,
    channel_menu_kb,
    channel_stats_kb,
    confirm_channel_kb,
    delete_section_kb,
    edit_channel_list_kb,
    edit_section_kb,
)
from states.admin_states import ChannelEditSG, ChannelSG
from utils import texts
from utils.filters import HasPerm, IsAdmin
from utils.helpers import channel_link, hhmm, invalidate_all_subscriptions, parse_chat_ref

log = logging.getLogger(__name__)
router = Router(name="admin:channels")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())

_KIND_INFO = {
    "base": texts.BASE_CHANNEL_INFO,
    "mandatory": texts.MANDATORY_CHANNEL_INFO,
    "request": texts.REQUEST_CHANNEL_INFO,
}
_KIND_LABEL = {"base": "📦 Baza", "mandatory": "🔒 Majburiy", "request": "📩 Zayavka"}


@router.message(F.text == BTN_CHANNELS)
async def channel_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        texts.CHANNEL_MENU,
        reply_markup=channel_menu_kb(q.has_perm(message.from_user.id, "channels")),
    )


@router.callback_query(F.data == "ch:back")
async def back_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.CHANNEL_MENU,
            reply_markup=channel_menu_kb(q.has_perm(call.from_user.id, "channels")),
        )
    await call.answer()


@router.callback_query(F.data.in_({"ch:base", "ch:mand", "ch:req"}), HasPerm("channels"))
async def channel_info(call: CallbackQuery):
    kind = {"ch:base": "base", "ch:mand": "mandatory", "ch:req": "request"}[call.data]
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(_KIND_INFO[kind], reply_markup=add_channel_kb(kind))
    await call.answer()


# ═══════════════════════════════════════════════════════
#                    ➕ KANAL QO'SHISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.startswith("ch:add:"), HasPerm("channels"))
async def ask_channel(call: CallbackQuery, state: FSMContext):
    kind = call.data.split(":")[2]

    # Baza kanal — bitta bo'ladi.
    if kind == "base" and q.base_channel() is not None:
        await call.answer(texts.BASE_EXISTS, show_alert=True)
        return

    await state.set_state(ChannelSG.chat)
    await state.update_data(kind=kind)
    prompt = texts.ASK_CHANNEL_ID if kind == "request" else texts.ASK_CHANNEL
    await call.message.answer(prompt, reply_markup=cancel_kb())
    await call.answer()


@router.message(ChannelSG.chat, F.text)
async def got_channel(message: Message, state: FSMContext, bot: Bot):
    ref = parse_chat_ref(message.text)
    if ref is None:
        await message.answer(texts.channel_failed("noto'g'ri format. @username yoki -100... kiriting."))
        return

    data = await state.get_data()
    kind = data["kind"]

    # 1) Kanal mavjudmi?
    try:
        chat = await bot.get_chat(ref)
    except TelegramAPIError as e:
        await message.answer(texts.channel_failed(f"kanal topilmadi ({e.message})."))
        return

    # 2) Takroriy emasmi?
    if q.channel_exists(chat.id):
        await message.answer(texts.CHANNEL_DUPLICATE)
        return

    # 3) Bot admin'mi?
    try:
        me = await bot.get_chat_member(chat.id, bot.id)
    except TelegramAPIError:
        await message.answer(texts.channel_failed("bot kanalda admin emas."))
        return
    if me.status not in {"administrator", "creator"}:
        await message.answer(texts.channel_failed("bot kanalda admin emas."))
        return

    invite_link: str | None = None
    if kind == "request":
        # Zayavka kanal: so'rov yaratuvchi maxsus link (TZ §7.2).
        try:
            link = await bot.create_chat_invite_link(chat.id, creates_join_request=True)
            invite_link = link.invite_link
        except TelegramAPIError as e:
            await message.answer(
                texts.channel_failed(
                    f"invite link yaratib bo'lmadi ({e.message}). "
                    "Botga «Invite users via link» huquqini bering."
                )
            )
            return
    elif not chat.username:
        # Majburiy/baza kanal private bo'lsa ham link kerak.
        try:
            link = await bot.create_chat_invite_link(chat.id)
            invite_link = link.invite_link
        except TelegramAPIError:
            invite_link = None

    await state.update_data(chat_id=chat.id, username=chat.username, invite_link=invite_link)

    # Baza kanalga alohida nom kerak emas.
    if kind == "base":
        await state.clear()
        await q.add_channel(chat.id, chat.username, chat.title or "Baza kanal", "base", invite_link)
        await message.answer(texts.BASE_ADDED, reply_markup=back_channel_kb())
        return

    await state.set_state(ChannelSG.title)
    await message.answer(texts.ASK_CHANNEL_TITLE, reply_markup=cancel_kb())


@router.message(ChannelSG.chat)
async def channel_not_text(message: Message):
    await message.answer(texts.NEED_TEXT)


@router.message(ChannelSG.title, F.text)
async def got_title(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()

    kind = data["kind"]
    await q.add_channel(
        chat_id=data["chat_id"],
        username=data["username"],
        title=message.text.strip()[:128],
        ctype=kind,
        invite_link=data["invite_link"],
    )
    # Kanallar ro'yxati o'zgardi → obuna keshi endi ishonchsiz.
    invalidate_all_subscriptions()

    await message.answer(
        texts.MANDATORY_ADDED if kind == "mandatory" else texts.REQUEST_ADDED,
        reply_markup=back_channel_kb(),
    )


# ═══════════════════════════════════════════════════════
#                  ✏️ KANALNI TAHRIRLASH
# ═══════════════════════════════════════════════════════

def _edit_card_text(chan: dict) -> str:
    return texts.channel_edit_card(
        chan["title"] or "Nomsiz",
        chan["username"],
        _KIND_LABEL.get(chan["ctype"], chan["ctype"]),
        chan["chat_id"],
        chan.get("invite_link"),
        is_base=chan["ctype"] == "base",
    )


@router.callback_query(F.data == "ch:edit", HasPerm("channels"))
async def edit_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.CHANNEL_EDIT_SECTION, reply_markup=edit_section_kb()
        )
    await call.answer()


@router.callback_query(F.data.startswith("chesec:"), HasPerm("channels"))
async def edit_section(call: CallbackQuery, state: FSMContext):
    await state.clear()
    kind = call.data.split(":")[1]
    channels = q.get_channels(kind)
    if not channels:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.channel_edit_list(_KIND_LABEL[kind], len(channels)),
            reply_markup=edit_channel_list_kb(channels),
        )
    await call.answer()


@router.callback_query(F.data.startswith("ched:"), HasPerm("channels"))
async def edit_card(call: CallbackQuery):
    row_id = int(call.data.split(":")[1])
    chan = q.get_channel_by_id(row_id)
    if chan is None:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            _edit_card_text(chan), reply_markup=channel_edit_kb(row_id, chan["ctype"])
        )
    await call.answer()


# ─────────── 📛 Nomni o'zgartirish ───────────

@router.callback_query(F.data.startswith("chedt:"), HasPerm("channels"))
async def ask_new_title(call: CallbackQuery, state: FSMContext):
    row_id = int(call.data.split(":")[1])
    chan = q.get_channel_by_id(row_id)
    if chan is None:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    await state.set_state(ChannelEditSG.title)
    await state.update_data(row_id=row_id)
    await call.message.answer(
        texts.ask_new_channel_title(chan["title"] or "Nomsiz"), reply_markup=cancel_kb()
    )
    await call.answer()


@router.message(ChannelEditSG.title, F.text)
async def save_new_title(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.clear()
    row_id = data["row_id"]

    if not await q.update_channel_title(row_id, message.text.strip()[:128]):
        await message.answer(texts.CHANNELS_EMPTY, reply_markup=back_channel_kb())
        return

    chan = q.get_channel_by_id(row_id)
    await message.answer(
        texts.CHANNEL_TITLE_UPDATED + "\n\n" + _edit_card_text(chan),
        reply_markup=channel_edit_kb(row_id, chan["ctype"]),
    )


@router.message(ChannelEditSG.title)
async def new_title_not_text(message: Message):
    await message.answer(texts.NEED_TEXT, reply_markup=cancel_kb())


# ─────────── 🔗 Username / kanalni o'zgartirish ───────────

@router.callback_query(F.data.startswith("chedu:"), HasPerm("channels"))
async def ask_new_chat(call: CallbackQuery, state: FSMContext):
    row_id = int(call.data.split(":")[1])
    if q.get_channel_by_id(row_id) is None:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    await state.set_state(ChannelEditSG.chat)
    await state.update_data(row_id=row_id)
    await call.message.answer(texts.ASK_NEW_CHANNEL_REF, reply_markup=cancel_kb())
    await call.answer()


@router.message(ChannelEditSG.chat, F.text)
async def save_new_chat(message: Message, state: FSMContext, bot: Bot):
    ref = parse_chat_ref(message.text)
    if ref is None:
        await message.answer(
            texts.channel_failed("noto'g'ri format. @username yoki -100... kiriting."),
            reply_markup=cancel_kb(),
        )
        return

    data = await state.get_data()
    row_id = data["row_id"]
    chan = q.get_channel_by_id(row_id)
    if chan is None:
        await state.clear()
        await message.answer(texts.CHANNELS_EMPTY, reply_markup=back_channel_kb())
        return
    kind = chan["ctype"]

    # 1) Kanal mavjudmi?
    try:
        chat = await bot.get_chat(ref)
    except TelegramAPIError as e:
        await message.answer(
            texts.channel_failed(f"kanal topilmadi ({e.message})."), reply_markup=cancel_kb()
        )
        return

    # 2) Boshqa yozuvda band emasmi? (o'zining joriy kanali — ruxsat: username yangilash)
    if chat.id != chan["chat_id"] and q.channel_exists(chat.id):
        await message.answer(texts.CHANNEL_DUPLICATE, reply_markup=cancel_kb())
        return

    # 3) Bot admin'mi?
    try:
        me = await bot.get_chat_member(chat.id, bot.id)
    except TelegramAPIError:
        me = None
    if me is None or me.status not in {"administrator", "creator"}:
        await message.answer(
            texts.channel_failed("bot kanalda admin emas."), reply_markup=cancel_kb()
        )
        return

    # 4) Havola: zayavka — so'rovli link, private — oddiy link.
    invite_link: str | None = None
    if kind == "request":
        try:
            link = await bot.create_chat_invite_link(chat.id, creates_join_request=True)
            invite_link = link.invite_link
        except TelegramAPIError as e:
            await message.answer(
                texts.channel_failed(
                    f"invite link yaratib bo'lmadi ({e.message}). "
                    "Botga «Invite users via link» huquqini bering."
                ),
                reply_markup=cancel_kb(),
            )
            return
    elif not chat.username:
        try:
            link = await bot.create_chat_invite_link(chat.id)
            invite_link = link.invite_link
        except TelegramAPIError:
            invite_link = None

    await state.clear()

    # Kanal butunlay almashgan bo'lsa — eski zayavkalar keraksiz.
    if chat.id != chan["chat_id"] and kind == "request":
        await q.drop_join_requests(chan["chat_id"])

    await q.update_channel_chat(row_id, chat.id, chat.username, invite_link)
    # Obuna holati endi boshqa kanalga bog'liq → keshni tozalaymiz.
    invalidate_all_subscriptions()

    chan = q.get_channel_by_id(row_id)
    await message.answer(
        texts.CHANNEL_CHAT_UPDATED + "\n\n" + _edit_card_text(chan),
        reply_markup=channel_edit_kb(row_id, chan["ctype"]),
    )


@router.message(ChannelEditSG.chat)
async def new_chat_not_text(message: Message):
    await message.answer(texts.NEED_TEXT, reply_markup=cancel_kb())


# ═══════════════════════════════════════════════════════
#                   🗑 KANAL O'CHIRISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "ch:del", HasPerm("channels"))
async def delete_menu(call: CallbackQuery):
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.ASK_DELETE_SECTION, reply_markup=delete_section_kb())
    await call.answer()


@router.callback_query(F.data.startswith("chsec:"), HasPerm("channels"))
async def delete_section(call: CallbackQuery):
    kind = call.data.split(":")[1]
    channels = q.get_channels(kind)
    if not channels:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            f"{_KIND_LABEL[kind]} kanallar ({len(channels)} ta)\n\n"
            "🗑 O'chirmoqchi bo'lganini tanlang:",
            reply_markup=channel_list_kb(channels),
        )
    await call.answer()


@router.callback_query(F.data.startswith("chdel:"), HasPerm("channels"))
async def confirm_delete(call: CallbackQuery):
    row_id = int(call.data.split(":")[1])
    chan = q.get_channel_by_id(row_id)
    if chan is None:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return
    link = channel_link(chan) or (f"@{chan['username']}" if chan["username"] else str(chan["chat_id"]))
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.confirm_channel_delete(chan["title"], link),
            reply_markup=confirm_channel_kb(row_id),
        )
    await call.answer()


@router.callback_query(F.data.startswith("chyes:"), HasPerm("channels"))
async def do_delete(call: CallbackQuery):
    row_id = int(call.data.split(":")[1])
    chan = q.get_channel_by_id(row_id)
    if chan is None:
        await call.answer(texts.CHANNELS_EMPTY, show_alert=True)
        return

    if chan["ctype"] == "request":
        await q.drop_join_requests(chan["chat_id"])
    await q.delete_channel(row_id)
    invalidate_all_subscriptions()

    await call.answer("✅ O'chirildi!")
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.CHANNEL_DELETED, reply_markup=back_channel_kb())


@router.callback_query(F.data == "chno")
async def cancel_delete(call: CallbackQuery):
    await call.answer(texts.CANCELLED)
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.CANCELLED, reply_markup=back_channel_kb())


# ═══════════════════════════════════════════════════════
#                 📊 KANAL STATISTIKA
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.in_({"ch:stats", "ch:stats_refresh"}))
async def channel_stats(call: CallbackQuery):
    text = texts.channel_stats_text(q.channel_stats(), hhmm())
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(text, reply_markup=channel_stats_kb())
    await call.answer("🔄 Yangilandi" if call.data == "ch:stats_refresh" else None)
