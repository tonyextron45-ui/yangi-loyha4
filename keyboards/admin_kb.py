"""Admin tugmalari."""

from __future__ import annotations

import math
from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import config

# ─────────── Asosiy menyu yorliqlari (handlerlarda filtr sifatida) ───────────
BTN_STATS = "📊 Statistika"
BTN_CONTENT = "🎬 Kino sozlamalari"
BTN_CHANNELS = "📡 Kanal sozlamalari"
BTN_ADMINS = "👑 Admin sozlamalari"
BTN_BROADCAST = "📨 Xabar yuborish"
BTN_NOTIFY = "🔔 Bildirishnoma"
BTN_PREMIUM = "💎 Premium obunachilar"
BTN_SETTINGS = "⚙️ Sozlamalar"

remove_kb = ReplyKeyboardRemove()


def main_menu() -> ReplyKeyboardMarkup:
    """Reply keyboard — column 2."""
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=BTN_STATS), KeyboardButton(text=BTN_CONTENT))
    kb.row(KeyboardButton(text=BTN_CHANNELS), KeyboardButton(text=BTN_ADMINS))
    kb.row(KeyboardButton(text=BTN_BROADCAST), KeyboardButton(text=BTN_NOTIFY))
    kb.row(KeyboardButton(text=BTN_PREMIUM), KeyboardButton(text=BTN_SETTINGS))
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Bo'limni tanlang 👇")


def cancel_kb(back: str = "cancel") -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data=back))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                      STATISTIKA
# ═══════════════════════════════════════════════════════

def stats_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="👥 Foydalanuvchilar", callback_data="upg:1"))
    kb.row(InlineKeyboardButton(text="🔍 Nofaollarni tekshirish", callback_data="st:scan"))
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="st:refresh"))
    return kb.as_markup()


def scan_confirm_kb() -> InlineKeyboardMarkup:
    """Skaner — uzoq davom etadigan amal, tasdiq so'raladi."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Boshlash", callback_data="st:scango"),
        InlineKeyboardButton(text="❌ Bekor", callback_data="st:back"),
    )
    return kb.as_markup()


def scan_done_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📊 Statistikaga qaytish", callback_data="st:back"))
    return kb.as_markup()


def users_kb(ids: list[int], page: int, total: int) -> InlineKeyboardMarkup:
    """Foydalanuvchilar — column 2, 10 tadan pagination."""
    per = config.users_per_page
    pages = max(1, math.ceil(total / per))

    kb = InlineKeyboardBuilder()
    for i in range(0, len(ids), 2):
        row = [
            InlineKeyboardButton(text=str(tid), callback_data=f"usr:{tid}")
            for tid in ids[i : i + 2]
        ]
        kb.row(*row)

    if pages > 1:
        kb.row(
            InlineKeyboardButton(text="◀️", callback_data=f"upg:{page - 1}"),
            InlineKeyboardButton(text=f"📄 {page}/{pages}", callback_data="noop"),
            InlineKeyboardButton(text="▶️", callback_data=f"upg:{page + 1}"),
        )
    kb.row(InlineKeyboardButton(text="🔍 ID orqali izlash", callback_data="usrfind"))
    kb.row(InlineKeyboardButton(text="🔙 Statistikaga qaytish", callback_data="st:back"))
    return kb.as_markup()


def user_card_kb(user: dict[str, Any], page: int = 1) -> InlineKeyboardMarkup:
    """Holatga qarab real vaqtda o'zgaradi."""
    kb = InlineKeyboardBuilder()
    tid = user["telegram_id"]
    kb.row(
        InlineKeyboardButton(text="➕ Balans qo'shish", callback_data=f"ubal:add:{tid}"),
        InlineKeyboardButton(text="➖ Balans ayirish", callback_data=f"ubal:sub:{tid}"),
    )
    if user["is_banned"]:
        kb.row(InlineKeyboardButton(text="🔓 Blokdan chiqarish", callback_data=f"uunblock:{tid}"))
    else:
        kb.row(InlineKeyboardButton(text="⛔️ Bloklash", callback_data=f"ublock:{tid}"))
    kb.row(InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data=f"upg:{page}"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                  KINO SOZLAMALARI
# ═══════════════════════════════════════════════════════

def content_menu_kb(can_edit: bool) -> InlineKeyboardMarkup:
    """Huquq yo'q bo'lsa — faqat statistika ko'rinadi (TZ §8.6.4)."""
    kb = InlineKeyboardBuilder()
    if can_edit:
        kb.row(InlineKeyboardButton(text="➕ Kino qo'shish", callback_data="c:add_movie"))
        kb.row(InlineKeyboardButton(text="➕ Serial qo'shish", callback_data="c:add_series"))
        kb.row(InlineKeyboardButton(text="🎞 Serialga qism qo'shish", callback_data="c:add_ep"))
        kb.row(InlineKeyboardButton(text="✏️ Tavsifni tahrirlash", callback_data="c:edit"))
        kb.row(InlineKeyboardButton(text="🗑 Kontent o'chirish", callback_data="c:del"))
    kb.row(InlineKeyboardButton(text="📊 Kontent statistika", callback_data="c:stats"))
    return kb.as_markup()


def content_type_kb(ctype: str) -> InlineKeyboardMarkup:
    """Kino/serial qo'shishda: bepul yoki pullik tanlash."""
    kb = InlineKeyboardBuilder()
    if ctype == "movie":
        kb.row(InlineKeyboardButton(text="🆓 Bepul kino", callback_data="c:addm:free"))
        kb.row(InlineKeyboardButton(text="💎 Pullik kino", callback_data="c:addm:paid"))
    else:
        kb.row(InlineKeyboardButton(text="🆓 Bepul serial", callback_data="c:adds:free"))
        kb.row(InlineKeyboardButton(text="💎 Pullik serial", callback_data="c:adds:paid"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="c:back"))
    return kb.as_markup()


def finish_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✅ Yakunlash", callback_data="c:finish"))
    kb.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"))
    return kb.as_markup()


def content_stats_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🏆 TOP 10", callback_data="c:top"))
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="c:stats_refresh"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="c:back"))
    return kb.as_markup()


def back_content_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="c:back"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                  KANAL SOZLAMALARI
# ═══════════════════════════════════════════════════════

def channel_menu_kb(can_edit: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_edit:
        kb.row(InlineKeyboardButton(text="📦 Baza kanal", callback_data="ch:base"))
        kb.row(InlineKeyboardButton(text="🔒 Majburiy obuna kanal", callback_data="ch:mand"))
        kb.row(InlineKeyboardButton(text="📩 Zayavka kanal", callback_data="ch:req"))
        kb.row(InlineKeyboardButton(text="✏️ Kanalni tahrirlash", callback_data="ch:edit"))
        kb.row(InlineKeyboardButton(text="🗑 Kanal o'chirish", callback_data="ch:del"))
    kb.row(InlineKeyboardButton(text="📊 Kanal statistika", callback_data="ch:stats"))
    return kb.as_markup()


def add_channel_kb(kind: str) -> InlineKeyboardMarkup:
    labels = {
        "base": "➕ Baza kanal qo'shish",
        "mandatory": "➕ Majburiy kanal qo'shish",
        "request": "➕ Zayavka kanal qo'shish",
    }
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text=labels[kind], callback_data=f"ch:add:{kind}"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:back"))
    return kb.as_markup()


def delete_section_kb() -> InlineKeyboardMarkup:
    """Column 2."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📦 Baza kanal", callback_data="chsec:base"),
        InlineKeyboardButton(text="🔒 Majburiy kanal", callback_data="chsec:mandatory"),
    )
    kb.row(
        InlineKeyboardButton(text="📩 Zayavka kanal", callback_data="chsec:request"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:back"),
    )
    return kb.as_markup()


def channel_list_kb(channels: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Column 1, tugma matni = admin bergan nom."""
    kb = InlineKeyboardBuilder()
    for chan in channels:
        kb.row(
            InlineKeyboardButton(text=f"📡 {chan['title']}", callback_data=f"chdel:{chan['id']}")
        )
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:del"))
    return kb.as_markup()


# ─────────── ✏️ KANALNI TAHRIRLASH ───────────

def edit_section_kb() -> InlineKeyboardMarkup:
    """Tahrirlash uchun bo'lim tanlash — column 2."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="📦 Baza kanal", callback_data="chesec:base"),
        InlineKeyboardButton(text="🔒 Majburiy kanal", callback_data="chesec:mandatory"),
    )
    kb.row(
        InlineKeyboardButton(text="📩 Zayavka kanal", callback_data="chesec:request"),
        InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:back"),
    )
    return kb.as_markup()


def edit_channel_list_kb(channels: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Column 1, tugma matni = @username (private bo'lsa — nom)."""
    kb = InlineKeyboardBuilder()
    for chan in channels:
        label = f"🔗 @{chan['username']}" if chan["username"] else f"📡 {chan['title']}"
        kb.row(InlineKeyboardButton(text=label[:40], callback_data=f"ched:{chan['id']}"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:edit"))
    return kb.as_markup()


def channel_edit_kb(row_id: int, kind: str) -> InlineKeyboardMarkup:
    """Kanal kartasi: nomni / username'ni o'zgartirish."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="📛 Nomni o'zgartirish", callback_data=f"chedt:{row_id}"))
    kb.row(InlineKeyboardButton(text="🔗 Username o'zgartirish", callback_data=f"chedu:{row_id}"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data=f"chesec:{kind}"))
    return kb.as_markup()


def confirm_channel_kb(row_id: int) -> InlineKeyboardMarkup:
    """Column 2."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"chyes:{row_id}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="chno"),
    )
    return kb.as_markup()


def channel_stats_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="ch:stats_refresh"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:back"))
    return kb.as_markup()


def back_channel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="ch:back"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                  ADMIN SOZLAMALARI
# ═══════════════════════════════════════════════════════

def admin_menu_kb(can_edit: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_edit:
        kb.row(InlineKeyboardButton(text="➕ Admin qo'shish", callback_data="a:add"))
    kb.row(InlineKeyboardButton(text="👥 Adminlar ro'yxati", callback_data="a:list"))
    if can_edit:
        kb.row(InlineKeyboardButton(text="🗑 Admin o'chirish", callback_data="a:del"))
    return kb.as_markup()


def admin_list_kb(admins: list[dict[str, Any]], action: str = "adm") -> InlineKeyboardMarkup:
    """Column 2, tugma matni = admin ID."""
    kb = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(
            text=("👑 " if a["role"] == "main" else "🟡 ") + str(a["telegram_id"]),
            callback_data=f"{action}:{a['telegram_id']}",
        )
        for a in admins
    ]
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i : i + 2])
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="a:back"))
    return kb.as_markup()


def admin_card_kb(admin: dict[str, Any], show_toggles: bool) -> InlineKeyboardMarkup:
    """Toggle tugmalari — faqat asosiy adminga ko'rinadi."""
    kb = InlineKeyboardBuilder()
    tid = admin["telegram_id"]
    if show_toggles and admin["role"] != "main":
        mark = lambda v: "✅" if v else "❌"  # noqa: E731
        kb.row(
            InlineKeyboardButton(
                text=f"🎬 Kino: {mark(admin['can_content'])}",
                callback_data=f"perm:{tid}:content",
            )
        )
        kb.row(
            InlineKeyboardButton(
                text=f"📡 Kanal: {mark(admin['can_channels'])}",
                callback_data=f"perm:{tid}:channels",
            )
        )
        kb.row(
            InlineKeyboardButton(
                text=f"👑 Admin: {mark(admin['can_admins'])}",
                callback_data=f"perm:{tid}:admins",
            )
        )
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="a:list"))
    return kb.as_markup()


def confirm_admin_kb(tid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"ayes:{tid}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="ano"),
    )
    return kb.as_markup()


def back_admin_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="a:back"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                BROADCAST / BILDIRISHNOMA
# ═══════════════════════════════════════════════════════

def broadcast_confirm_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Yuborish", callback_data="bc:yes"),
        InlineKeyboardButton(text="❌ Bekor qilish", callback_data="cancel"),
    )
    return kb.as_markup()


def notify_kb(is_on: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    label = "🔕 O'chirish" if is_on else "🔔 Yoqish"
    kb.row(InlineKeyboardButton(text=label, callback_data="nt:toggle"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                💳 TO'LOV TASDIQLASH
# ═══════════════════════════════════════════════════════

def payment_action_kb(pid: int) -> InlineKeyboardMarkup:
    """To'lov cheki ostidagi — tasdiqlash / rad etish (column 2)."""
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Tasdiqlash", callback_data=f"pay:ok:{pid}"),
        InlineKeyboardButton(text="❌ Rad etish", callback_data=f"pay:no:{pid}"),
    )
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#              💎 PREMIUM OBUNACHILAR
# ═══════════════════════════════════════════════════════

def premium_subs_kb(ids: list[int]) -> InlineKeyboardMarkup:
    """Faol premium obunachilar — column 2, ID bo'yicha."""
    kb = InlineKeyboardBuilder()
    buttons = [
        InlineKeyboardButton(text=f"💎 {tid}", callback_data=f"psub:{tid}") for tid in ids
    ]
    for i in range(0, len(buttons), 2):
        kb.row(*buttons[i : i + 2])
    kb.row(InlineKeyboardButton(text="🔄 Yangilash", callback_data="psubs"))
    return kb.as_markup()


def premium_sub_card_kb(tid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🚫 Obunani bekor qilish", callback_data=f"pcancel:{tid}"))
    kb.row(InlineKeyboardButton(text="🔙 Ro'yxatga qaytish", callback_data="psubs"))
    return kb.as_markup()


def confirm_cancel_premium_kb(tid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"pcyes:{tid}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"psub:{tid}"),
    )
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#                    ⚙️ SOZLAMALAR
# ═══════════════════════════════════════════════════════

def settings_menu_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💳 To'lov kartalari", callback_data="set:cards"))
    kb.row(InlineKeyboardButton(text="💎 Premium narxlari", callback_data="set:tariffs"))
    kb.row(InlineKeyboardButton(text="🆘 Yordam limiti", callback_data="set:help"))
    kb.row(InlineKeyboardButton(text="👥 Referal narxi", callback_data="set:ref"))
    return kb.as_markup()


def referral_setting_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="set:ref_edit"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="set:back"))
    return kb.as_markup()


def back_settings_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔙 Sozlamalarga qaytish", callback_data="set:back"))
    return kb.as_markup()


def cards_manage_kb(cards: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    for c in cards:
        label = f"💳 {c['number']}"
        kb.row(InlineKeyboardButton(text=label[:40], callback_data=f"card:{c['id']}"))
    kb.row(InlineKeyboardButton(text="➕ Karta qo'shish", callback_data="card:add"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="set:back"))
    return kb.as_markup()


def card_actions_kb(cid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✏️ Tahrirlash", callback_data=f"card:edit:{cid}"),
        InlineKeyboardButton(text="🗑 O'chirish", callback_data=f"card:del:{cid}"),
    )
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="set:cards"))
    return kb.as_markup()


def confirm_card_delete_kb(cid: int) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"card:delyes:{cid}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data=f"card:{cid}"),
    )
    return kb.as_markup()


def tariffs_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="🎫 1 oy", callback_data="tar:1m"),
        InlineKeyboardButton(text="🎫 3 oy", callback_data="tar:3m"),
    )
    kb.row(
        InlineKeyboardButton(text="🎫 6 oy", callback_data="tar:6m"),
        InlineKeyboardButton(text="🎫 1 yil", callback_data="tar:1y"),
    )
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="set:back"))
    return kb.as_markup()


def help_limit_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="✏️ O'zgartirish", callback_data="set:help_edit"))
    kb.row(InlineKeyboardButton(text="🔙 Orqaga", callback_data="set:back"))
    return kb.as_markup()
