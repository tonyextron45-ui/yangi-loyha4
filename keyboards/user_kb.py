"""Foydalanuvchi tugmalari."""

from __future__ import annotations

import math
from typing import Any

from aiogram.types import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardMarkup,
)
from aiogram.utils.keyboard import InlineKeyboardBuilder, ReplyKeyboardBuilder

from config import config
from utils.helpers import channel_link


def _num(value: int) -> str:
    return f"{int(value):,}".replace(",", " ")


# ═══════════════════════════════════════════════════════
#              PASTKI MENYU (Reply keyboard)
# ═══════════════════════════════════════════════════════

BTN_BALANCE = "💰 Balans"
BTN_PREMIUM = "💎 Premium obuna"
BTN_REFERRAL = "👥 Referal"
BTN_HELP = "🆘 Yordam"


def user_menu() -> ReplyKeyboardMarkup:
    """/start ostidagi doimiy menyu — column 2."""
    kb = ReplyKeyboardBuilder()
    kb.row(KeyboardButton(text=BTN_BALANCE), KeyboardButton(text=BTN_PREMIUM))
    kb.row(KeyboardButton(text=BTN_REFERRAL), KeyboardButton(text=BTN_HELP))
    return kb.as_markup(resize_keyboard=True, input_field_placeholder="Kino kodini yuboring 🔢")


def referral_kb(link: str) -> InlineKeyboardMarkup:
    """Referal havolasini ulashish tugmasi."""
    share = (
        "https://t.me/share/url?url=" + link +
        "&text=" + "🎬 Eng sara kino va seriallar shu botda! Qo'shiling 👇"
    )
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="🔗 Do'stlarga ulashish", url=share))
    return kb.as_markup()


def user_cancel_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="❌ Bekor qilish", callback_data="ucancel"))
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#              BALANS / PREMIUM / TO'LDIRISH
# ═══════════════════════════════════════════════════════

def topup_button_kb() -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💳 Balansni to'ldirish", callback_data="topup"))
    return kb.as_markup()


def premium_tariffs_kb(prices: dict[str, int], *, back: bool = False) -> InlineKeyboardMarkup:
    """Premium tariflar — column 2.

    `back=True` — panel majburiy obuna to'sig'idan («💎 Obunasiz ko'rish»)
    ochilgan: eng pastda column 1 bo'lib «⬅️ Ortga» tugmasi qo'shiladi.
    """
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text=f"1 oy · {_num(prices['1m'])}", callback_data="prem:1m"),
        InlineKeyboardButton(text=f"3 oy · {_num(prices['3m'])}", callback_data="prem:3m"),
    )
    kb.row(
        InlineKeyboardButton(text=f"6 oy · {_num(prices['6m'])}", callback_data="prem:6m"),
        InlineKeyboardButton(text=f"1 yil · {_num(prices['1y'])}", callback_data="prem:1y"),
    )
    if back:
        kb.row(InlineKeyboardButton(text="⬅️ Ortga", callback_data="backsub"))
    return kb.as_markup()


def premium_offer_kb() -> InlineKeyboardMarkup:
    """Majburiy obuna to'sig'idagi foydalanuvchini premium panelga qaytaradi
    (masalan balansi to'ldirilgach)."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="💎 Premium obuna olish", callback_data="nosub"))
    return kb.as_markup()


def premium_confirm_kb(tariff: str) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(text="✅ Ha", callback_data=f"premyes:{tariff}"),
        InlineKeyboardButton(text="❌ Yo'q", callback_data="premno"),
    )
    return kb.as_markup()


# ═══════════════════════════════════════════════════════
#              PULLIK KINO / SERIAL SOTIB OLISH
# ═══════════════════════════════════════════════════════

def paid_movie_kb(code: int, price: int, can_afford: bool) -> InlineKeyboardMarkup:
    """Balans yetsa — «X so'm evaziga ko'rish», aks holda «Sotib olish»."""
    kb = InlineKeyboardBuilder()
    if can_afford:
        kb.row(InlineKeyboardButton(
            text=f"💳 {_num(price)} so'm evaziga ko'rish", callback_data=f"buypay:{code}"))
    else:
        kb.row(InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buyup:{code}"))
    return kb.as_markup()


def paid_series_kb(code: int, price: int, can_afford: bool) -> InlineKeyboardMarkup:
    kb = InlineKeyboardBuilder()
    if can_afford:
        kb.row(InlineKeyboardButton(
            text=f"💳 {_num(price)} so'm evaziga sotib olish", callback_data=f"buypay:{code}"))
    else:
        kb.row(InlineKeyboardButton(text="🛒 Sotib olish", callback_data=f"buyup:{code}"))
    return kb.as_markup()


def subscription_kb(channels: list[dict[str, Any]]) -> InlineKeyboardMarkup:
    """Obuna paneli — column 1, har bir kanal admin bergan nom bilan.

    `channels` — foydalanuvchi obuna bo'lMAGAN kanallar (yetishmayotganlari).
    Ya'ni 4 tadan 1 tasidan chiqib ketsa, panelda FAQAT o'sha 1 tasi ko'rinadi.
    """
    kb = InlineKeyboardBuilder()
    for chan in channels:
        link = channel_link(chan)
        if not link:
            continue
        icon = "📩" if chan["ctype"] == "request" else "🟢"
        kb.row(InlineKeyboardButton(text=f"{icon} {chan['title']}", url=link))
    # Pastki qator — column 2: tekshirish va premium yo'li yonma-yon.
    kb.row(
        InlineKeyboardButton(text="✅ Tekshirish", callback_data="check_sub"),
        InlineKeyboardButton(text="💎 Obunasiz ko'rish", callback_data="nosub"),
    )
    return kb.as_markup()


def movie_watch_kb(code: int) -> InlineKeyboardMarkup:
    """Kino kartasi ostidagi «▶️ Kinoni ko'rish» tugmasi."""
    kb = InlineKeyboardBuilder()
    kb.row(InlineKeyboardButton(text="▶️ Kinoni ko'rish", callback_data=f"watch:{code}"))
    return kb.as_markup()


def series_kb(code: int, page: int, ep_numbers: list[int]) -> InlineKeyboardMarkup:
    """Qism tugmalari — column 2, sahifalab (config.episodes_per_page).

    `ep_numbers` — bazadagi HAQIQIY qism raqamlari (tartiblangan). Shu tufayli
    biror qism o'chirilib bo'shliq qolса ham (masalan 1, 2, 4, 5) tugmalar
    faqat mavjud qismlarni ko'rsatadi.
    """
    per = config.episodes_per_page
    pages = max(1, math.ceil(len(ep_numbers) / per))
    page = max(1, min(page, pages))

    kb = InlineKeyboardBuilder()
    start = (page - 1) * per
    chunk = ep_numbers[start : start + per]
    # 2 tadan qatorga (column 2).
    for i in range(0, len(chunk), 2):
        kb.row(
            *(
                InlineKeyboardButton(text=f"▶️ {ep}-qism", callback_data=f"ep:{code}:{ep}")
                for ep in chunk[i : i + 2]
            )
        )

    if pages > 1:
        kb.row(
            InlineKeyboardButton(text="◀️", callback_data=f"ser:{code}:{page - 1}"),
            InlineKeyboardButton(text=f"📄 {page}/{pages}", callback_data="noop"),
            InlineKeyboardButton(text="▶️", callback_data=f"ser:{code}:{page + 1}"),
        )
    return kb.as_markup()


def share_kb(code: int, bot_username: str) -> InlineKeyboardMarkup:
    """Deep link ulashish — organik o'sish uchun."""
    url = f"https://t.me/{bot_username}?start={code}"
    kb = InlineKeyboardBuilder()
    kb.row(
        InlineKeyboardButton(
            text="🔗 Ulashish",
            url=f"https://t.me/share/url?url={url}",
        )
    )
    return kb.as_markup()
