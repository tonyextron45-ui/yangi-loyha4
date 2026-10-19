"""Barcha premium UI matn shablonlari — yagona uslub markazi.

Dizayn qoidalari (TZ §13):
  • Ramka:      ╭── ... ──╮ / ╰── ... ──╯
  • Ajratuvchi: ━━━━━━━━━━
  • HTML teglar: <b> <i> <code>
  • Har bir tugma emoji bilan boshlanadi
"""

from __future__ import annotations

from html import escape

DIVIDER = "━━━━━━━━━━━━━━━━━━"


def num(value: int | float) -> str:
    """12450 → «12 450» (premium ko'rinish uchun probel bilan)."""
    return f"{int(value):,}".replace(",", " ")


def esc(text: str | None) -> str:
    return escape(text or "", quote=False)


# ═══════════════════════════════════════════════════════
#                    FOYDALANUVCHI
# ═══════════════════════════════════════════════════════

def welcome(name: str) -> str:
    return (
        "╭─────────────────────╮\n"
        "   🎬 <b>Tarjima Kinoman Bot</b>\n"
        "╰─────────────────────╯\n\n"
        f"👋 Assalomu alaykum, <b>{esc(name)}</b>!\n\n"
        "🍿 Minglab kino va seriallar — bir kod bilan!\n\n"
        "🎯 Foydalanish juda oson:\n"
        "🔢 Kino kodini yuboring\n"
        "➡️ Bot darhol taqdim etadi\n\n"
        f"{DIVIDER}\n"
        "✨ <i>Yoqimli tomosha tilaymiz!</i> ✨"
    )


SUBSCRIPTION_PANEL = (
    "╭────────────────────╮\n"
    "    🔒 <b>MAJBURIY OBUNA</b>\n"
    "╰────────────────────╯\n\n"
    "📢 Botdan to'liq foydalanish uchun\n"
    "quyidagi kanallarga obuna bo'ling 👇\n\n"
    "💡 Obuna bo'lgach «✅ Tekshirish»\n"
    "tugmasini bosing!\n\n"
    f"{DIVIDER}\n"
    "👑 <i>Obuna bo'lishni xohlamaysizmi?</i>\n"
    "💎 <b>Premium</b> olsangiz — kanallarga\n"
    "obuna bo'lmasdan kino ko'rasiz!"
)

SUB_CONFIRMED = "🎉 <b>Obuna tasdiqlandi!</b>\n\n🔢 Endi kino kodini yuboring 👇"
SUB_NOT_ENOUGH = "❌ Siz hali barcha kanallarga obuna bo'lmadingiz!"


def sub_not_enough(missing: int) -> str:
    """Ogohlantirish — nechta kanal QOLGANINI aniq aytadi."""
    if missing == 1:
        return "❌ Yana 1 ta kanalga obuna bo'lishingiz kerak!"
    return f"❌ Yana {missing} ta kanalga obuna bo'lishingiz kerak!"

NOT_A_NUMBER = "🔢 Iltimos, faqat kino kodini yuboring!\n<i>(masalan: 10001)</i>"
MOVIE_NOT_FOUND = (
    "❌ <b>Bunday kodli kino topilmadi!</b>\n\n🔍 Kodni tekshirib, qaytadan yuboring."
)
UNKNOWN_COMMAND = "❌ Noma'lum buyruq"


HEAVY = "━━━━━━━━━━━━━━━━━"


def content_body(
    title: str, genre: str, year: str, duration: str, language: str, *, icon: str = "🎬"
) -> str:
    """Qadamma-qadam yig'ilgan tavsif tanasi (footer'siz — bazada shu saqlanadi)."""
    return (
        "╭━━━━━━━━━━━━━━━╮\n"
        f"   {icon} <b>{esc(title)}</b>\n"
        "╰━━━━━━━━━━━━━━━╯\n\n"
        f"🎭 Janr: {esc(genre)}\n"
        f"📅 Yil: {esc(year)}\n"
        f"🕐 Davomiyligi: {esc(duration)}\n"
        f"🇺🇿 Til: {esc(language)}"
    )


def _footer(code: int, bot_username: str) -> str:
    """Bot avtomatik qo'shadigan qism — kod va username."""
    return f"{HEAVY}\n🔢 Kod: <code>{code}</code> | 🤖 @{bot_username}"


def movie_card(body: str, code: int, bot_username: str) -> str:
    """Kino kodini kiritganda ko'rinadigan trailer ostidagi tavsif."""
    return f"{body}\n{_footer(code, bot_username)}"


def series_card(body: str, code: int, bot_username: str, episodes: int) -> str:
    """Serial kodini kiritganda: trailer ostidagi tavsif + qism tugmalari sarlavhasi."""
    return (
        f"{body}\n{_footer(code, bot_username)}\n"
        f"📺 Qismlar: {num(episodes)} ta\n\n"
        "👇 <b>Qismni tanlang:</b>"
    )


def paid_movie_card(body: str, code: int, bot_username: str, price: int) -> str:
    """Pullik kino kartasi — pastida narx ko'rsatiladi (hali sotib olinmagan)."""
    return (
        f"{body}\n{_footer(code, bot_username)}\n"
        f"{HEAVY}\n"
        "💎 <b>Bu — pullik kino</b>\n"
        f"💰 Ushbu film narxi: <b>{num(price)} so'm</b>"
    )


def paid_series_card(body: str, code: int, bot_username: str, episodes: int, price: int) -> str:
    """Pullik serial kartasi — bir marta sotib olib, barcha qismlar ochiladi."""
    return (
        f"{body}\n{_footer(code, bot_username)}\n"
        f"📺 Qismlar: {num(episodes)} ta\n"
        f"{HEAVY}\n"
        "💎 <b>Bu — pullik serial</b>\n"
        f"💰 Ushbu serial narxi: <b>{num(price)} so'm</b>\n"
        "<i>Bir marta sotib olib, barcha qismlarni ko'rasiz.</i>"
    )


def movie_watch_caption(title: str, code: int, bot_username: str) -> str:
    """«▶️ Kinoni ko'rish» bosilganda kelgan to'liq film caption'i."""
    return (
        f"🎬 <b>{esc(title)}</b>\n"
        f"{_footer(code, bot_username)}"
    )


def episode_caption(title: str, code: int, ep: int, bot_username: str) -> str:
    return (
        f"📺 <b>{esc(title)} — {ep}-qism</b>\n"
        f"{_footer(code, bot_username)}"
    )


def new_user_alert(name: str, username: str | None, tid: int, when: str) -> str:
    return (
        "🟢 <b>Yangi foydalanuvchi!</b>\n\n"
        f"👤 Ism: {esc(name)}\n"
        f"🔗 Username: {('@' + username) if username else '—'}\n"
        f"🆔 ID: <code>{tid}</code>\n"
        f"🕐 {when}"
    )


def left_user_alert(name: str, tid: int, when: str) -> str:
    return (
        "🔴 <b>Foydalanuvchi botni tark etdi!</b>\n\n"
        f"👤 Ism: {esc(name)}\n"
        f"🆔 ID: <code>{tid}</code>\n"
        f"🕐 {when}"
    )


# ═══════════════════════════════════════════════════════
#                       BLOKLASH
# ═══════════════════════════════════════════════════════

def banned_notice(minutes: int) -> str:
    return f"⛔️ Siz admin tomonidan <b>{minutes} daqiqaga</b> bloklandingiz!"


def ban_active(minutes_left: int) -> str:
    return (
        "⛔️ <b>Siz admin tomonidan bloklangansiz!</b>\n"
        f"⏳ Qolgan vaqt: <b>{minutes_left} daqiqa</b>"
    )


BAN_EXPIRED = "✅ <b>Bloklash vaqti tugadi!</b>\nBotdan yana foydalanishingiz mumkin 🎬"
UNBANNED_BY_ADMIN = "🔓 Siz admin tomonidan blokdan chiqarildingiz!"
ASK_BAN_MINUTES = "⏱ <b>Necha daqiqaga bloklaysiz?</b>\n\n<i>(masalan: 60)</i>"
NOT_A_MINUTE = "⚠️ Faqat raqam kiriting! <i>(masalan: 60)</i>"


# ═══════════════════════════════════════════════════════
#                     ADMIN PANEL
# ═══════════════════════════════════════════════════════

ASK_PASSWORD = "🔐 <b>ADMIN PANEL</b>\n\nKirish uchun parolni kiriting:"
WRONG_PASSWORD = "❌ Noto'g'ri parol! Qaytadan urinib ko'ring."


def password_locked(minutes: int) -> str:
    return f"⏳ Juda ko'p urinish! <b>{minutes} daqiqadan</b> so'ng qayta urining."


def admin_panel(name: str, role: str, when: str) -> str:
    badge = "👑 Asosiy admin" if role == "main" else "🟡 Yordamchi admin"
    return (
        "╭───────────────────╮\n"
        "    🔐 <b>ADMIN PANEL</b>\n"
        "╰───────────────────╯\n\n"
        f"Xush kelibsiz, <b>{esc(name)}</b>! 👋\n\n"
        f"👑 Maqom: {badge}\n"
        f"🕐 {when}\n\n"
        "📋 Kerakli bo'limni tanlang:"
    )


NO_PERMISSION = "⛔️ Sizda bu amal uchun huquq yo'q!"
CANCELLED = "↩️ Amal bekor qilindi."


# ═══════════════════════════════════════════════════════
#                      STATISTIKA
# ═══════════════════════════════════════════════════════

def _percent(part: int, whole: int) -> str:
    return f"{round(part / whole * 100)}%" if whole else "0%"


def bot_stats(s: dict, when: str) -> str:
    return (
        "╭── 📊 <b>BOT STATISTIKASI</b> ──╮\n\n"
        f"👥 Jami foydalanuvchilar: <b>{num(s['total'])}</b>\n"
        f"🟢 Faol: <b>{num(s['active'])}</b> <i>({_percent(s['active'], s['total'])})</i>\n"
        f"⛔️ Admin bloklagan: <b>{num(s['banned'])}</b>\n\n"
        f"{DIVIDER}\n"
        f"😴 <b>NOFAOL: {num(s['inactive'])}</b> ta "
        f"<i>({_percent(s['inactive'], s['total'])})</i>\n"
        f"{DIVIDER}\n"
        f"🔴 Botni bloklagan: <b>{num(s['blocked'])}</b>\n"
        f"🚪 Botni tark etgan: <b>{num(s['gone'])}</b>\n"
        f"💀 O'chirilgan akkaunt: <b>{num(s['deleted'])}</b>\n"
        "<i>(Telegram akkaunti o'chirilgan — xabar\nyetib bormaydi)</i>\n\n"
        f"{DIVIDER}\n"
        f"📈 Bugun: <b>+{num(s['today'])}</b>  ·  "
        f"7 kun: <b>+{num(s['week'])}</b>  ·  "
        f"30 kun: <b>+{num(s['month'])}</b>\n\n"
        "🎬 <b>Tarjima Kinoman Bot</b>\n"
        f"🕐 Yangilandi: {when}\n"
        "╰────────────────────╯"
    )


# ─────────── Nofaol akkauntlarni tekshirish (skaner) ───────────

SCAN_RUNNING = "⏳ Tekshiruv allaqachon ketmoqda — tugashini kuting!"
SCAN_NO_USERS = "📭 Tekshirish uchun foydalanuvchi yo'q!"


def scan_intro(total: int, eta: str) -> str:
    return (
        "╭── 🔍 <b>NOFAOL TEKSHIRUVI</b> ──╮\n\n"
        "Har bir akkaunt jimgina tekshiriladi va\n"
        "haqiqiy holati aniqlanadi:\n\n"
        "💀 Telegram akkaunti o'chirilgan\n"
        "🔴 Botni bloklagan\n"
        "🟢 Faol (qayta tiklangan)\n\n"
        f"{DIVIDER}\n"
        f"👥 Tekshiriladi: <b>{num(total)}</b> ta\n"
        f"⏱ Taxminiy vaqt: <b>{eta}</b>\n"
        f"{DIVIDER}\n"
        "🔕 <i>Foydalanuvchilarga hech qanday\nxabar bormaydi.</i>\n\n"
        "❓ Boshlaymizmi?\n"
        "╰─────────────────────╯"
    )


def scan_progress(done: int, total: int, deleted: int, blocked: int) -> str:
    pct = int(done / total * 100) if total else 100
    bar = "█" * (pct // 10) + "░" * (10 - pct // 10)
    return (
        "╭── 🔍 <b>NOFAOL TEKSHIRUVI</b> ──╮\n\n"
        f"<code>{bar}</code>  <b>{pct}%</b>\n\n"
        f"🔄 Tekshirildi: <b>{num(done)}</b> / {num(total)}\n"
        f"💀 O'chirilgan: <b>{num(deleted)}</b>\n"
        f"🔴 Bloklagan: <b>{num(blocked)}</b>\n\n"
        "<i>Iltimos, kuting...</i>\n"
        "╰─────────────────────╯"
    )


def scan_done(total: int, deleted: int, blocked: int, revived: int, elapsed: str) -> str:
    return (
        "╭── ✅ <b>TEKSHIRUV TUGADI</b> ──╮\n\n"
        f"🔄 Tekshirildi: <b>{num(total)}</b> ta akkaunt\n"
        f"{DIVIDER}\n"
        f"💀 O'chirilgan akkaunt: <b>{num(deleted)}</b>\n"
        f"🔴 Botni bloklagan: <b>{num(blocked)}</b>\n"
        f"🟢 Qayta faollashgan: <b>{num(revived)}</b>\n"
        f"{DIVIDER}\n"
        f"⏱ Sarflangan vaqt: <b>{elapsed}</b>\n\n"
        "<i>📊 Statistika yangilandi</i>\n"
        "╰─────────────────────╯"
    )


def user_card(u: dict, joined: str, status_line: str, premium_line: str) -> str:
    name = esc(u["full_name"]) or "Noma'lum"
    uname = f"@{u['username']}" if u["username"] else "—"
    return (
        "╭── 👤 <b>FOYDALANUVCHI</b> ──╮\n\n"
        f"🆔 ID: <code>{u['telegram_id']}</code>\n"
        f"👤 Ism: {name}\n"
        f"🔗 Username: {uname}\n"
        f"📅 Qo'shilgan: {joined}\n"
        f"📦 Holat: {status_line}\n"
        f"{DIVIDER}\n"
        f"💰 Balans: <b>{num(int(u.get('balance') or 0))} so'm</b>\n"
        f"{premium_line}\n"
        "╰───────────────────╯"
    )


USERS_EMPTY = "📭 Hali foydalanuvchi yo'q!"

ASK_USER_ID_SEARCH = (
    "🔍 <b>Foydalanuvchi Telegram ID sini kiriting:</b>\n"
    "<i>(masalan: 123456789)</i>"
)
USER_SEARCH_NOT_FOUND = (
    "❌ <b>Bu ID bilan foydalanuvchi topilmadi!</b>\n\n"
    "🔢 Boshqa ID kiriting yoki «❌ Bekor qilish» tugmasini bosing."
)


def ask_balance_amount(op: str, tid: int) -> str:
    if op == "add":
        return (
            f"➕ <code>{tid}</code> balansiga <b>qancha so'm qo'shasiz?</b>\n"
            "<i>Faqat raqam kiriting (masalan: 10000)</i>"
        )
    return (
        f"➖ <code>{tid}</code> balansidan <b>qancha so'm ayirasiz?</b>\n"
        "<i>Faqat raqam kiriting (masalan: 10000)</i>"
    )


def balance_admin_added(tid: int, amount: int, balance: int) -> str:
    return (
        f"✅ <code>{tid}</code> balansiga <b>+{num(amount)} so'm</b> qo'shildi!\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>"
    )


def balance_admin_deducted(tid: int, amount: int, balance: int) -> str:
    return (
        f"✅ <code>{tid}</code> balansidan <b>−{num(amount)} so'm</b> ayirildi!\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>"
    )


def balance_admin_insufficient(tid: int, balance: int) -> str:
    return (
        f"⚠️ Ayirib bo'lmadi — <code>{tid}</code> balansida\n"
        f"atigi <b>{num(balance)} so'm</b> bor!"
    )


def balance_added_notice(amount: int, balance: int) -> str:
    """Foydalanuvchiga: admin balans to'ldirdi."""
    return (
        "╭── 💰 <b>BALANS TO'LDIRILDI</b> ──╮\n\n"
        f"➕ Qo'shildi: <b>+{num(amount)} so'm</b>\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>\n"
        "╰──────────────────────╯\n\n"
        "🎬 Yoqimli tomosha tilaymiz!"
    )


def balance_deducted_notice(amount: int, balance: int) -> str:
    """Foydalanuvchiga: admin balansdan yechdi."""
    return (
        "╭── 💰 <b>BALANS O'ZGARDI</b> ──╮\n\n"
        f"➖ Yechildi: <b>−{num(amount)} so'm</b>\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>\n"
        "╰──────────────────────╯\n\n"
        "Savollar bo'lsa «🆘 Yordam» orqali murojaat qiling."
    )


# ═══════════════════════════════════════════════════════
#                  KINO SOZLAMALARI
# ═══════════════════════════════════════════════════════

CONTENT_MENU = (
    "╭── 🎬 <b>KINO SOZLAMALARI</b> ──╮\n\n"
    "Bu bo'limda siz:\n"
    "➕ Kino va serial qo'shishingiz\n"
    "🗑 Kod orqali bazadan o'chirishingiz\n"
    "📊 Faol va o'chirilgan kontentlar\n"
    "    sonini ko'rishingiz mumkin!\n"
    "╰─────────────────────╯"
)

NO_BASE_CHANNEL = "⚠️ Avval baza kanal qo'shing!\n<i>(📡 Kanal sozlamalari bo'limida)</i>"
BOT_NOT_ADMIN_BASE = "⚠️ Bot baza kanalda admin emas! Botni admin qiling."

ADD_MOVIE_HEADER = (
    "╭── ➕ <b>KINO QO'SHISH</b> ──╮\n\n"
    "Bot qadamma-qadam so'raydi:\n"
    "① Nomi ② Janr ③ Yil\n"
    "④ Davomiyligi ⑤ Tili\n"
    "⑥ Trailer ⑦ To'liq kino\n"
    "✅ Kod avtomatik beriladi!\n"
    "╰───────────────────╯"
)

ADD_SERIES_HEADER = (
    "╭── ➕ <b>SERIAL QO'SHISH</b> ──╮\n\n"
    "Bot qadamma-qadam so'raydi:\n"
    "① Nomi ② Janr ③ Yil\n"
    "④ Davomiyligi ⑤ Tili\n"
    "⑥ Trailer ⑦ Qismlar\n"
    "✅ Kod avtomatik beriladi!\n"
    "╰────────────────────╯"
)

# Qadamma-qadam tavsif so'rovlari
ASK_TITLE = "🎬 <b>Nomini kiriting:</b>\n<i>(masalan: OPPENHEIMER)</i>"
ASK_GENRE = "🎭 <b>Janrini kiriting:</b>\n<i>(masalan: Drama, Tarixiy)</i>"
ASK_YEAR = "📅 <b>Yilini kiriting:</b>\n<i>(masalan: 2023)</i>"
ASK_DURATION = "🕐 <b>Davomiyligini kiriting:</b>\n<i>(masalan: 180 daqiqa)</i>"
ASK_LANGUAGE = "🇺🇿 <b>Tilini kiriting:</b>\n<i>(masalan: O'zbek tilida)</i>"
ASK_TRAILER = (
    "🎞 <b>Trailer yuboring</b> <i>(video yoki rasm)</i>:\n\n"
    "<i>Foydalanuvchi kodni kiritganda shu ko'rinadi.</i>"
)
ASK_MOVIE_FILE = "🎥 <b>Endi to'liq kino videosini yuboring:</b>"

NEED_VIDEO = "⚠️ Iltimos, video yuboring!"
NEED_TEXT = "⚠️ Iltimos, matn yuboring!"
NEED_MEDIA = "⚠️ Iltimos, video yoki rasm yuboring!"


def _paid_badge(is_paid: bool, price: int) -> str:
    if is_paid:
        return f"💎 Turi: <b>Pullik</b>\n💰 Narxi: <b>{num(price)} so'm</b>\n"
    return "🆓 Turi: <b>Bepul</b>\n"


def movie_added(code: int, when: str, bot_username: str, is_paid: bool = False, price: int = 0) -> str:
    return (
        "╭──────────────────╮\n"
        "   ✅ <b>KINO QO'SHILDI!</b>\n"
        "╰──────────────────╯\n\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"{_paid_badge(is_paid, price)}"
        "📦 Baza kanalga joylandi\n"
        f"🕐 {when}\n\n"
        "🎬 Foydalanuvchilar endi\n"
        f"<code>{code}</code> kodi bilan olishlari mumkin!"
    )


ASK_FIRST_EPISODE = "📥 <b>1-qismni yuboring:</b>"


def episode_added(ep: int) -> str:
    return f"✅ <b>{ep}-qism</b> qo'shildi! Keyingi qismni yuboring yoki yakunlang 👇"


NEED_ONE_EPISODE = "⚠️ Kamida 1 ta qism yuklang!"


def series_added(code: int, count: int, is_paid: bool = False, price: int = 0) -> str:
    return (
        "╭──────────────────╮\n"
        "  ✅ <b>SERIAL QO'SHILDI!</b>\n"
        "╰──────────────────╯\n\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"📺 Qismlar: <b>{num(count)} ta</b>\n"
        f"{_paid_badge(is_paid, price)}"
        "📦 Baza kanalga joylandi"
    )


ASK_SERIES_CODE = "🔢 <b>Serial kodini kiriting:</b>"
SERIES_NOT_FOUND = "❌ Bunday kodli serial topilmadi!"


def episodes_appended(code: int, count: int, total: int) -> str:
    return (
        "╭──────────────────╮\n"
        "  ✅ <b>QISMLAR QO'SHILDI!</b>\n"
        "╰──────────────────╯\n\n"
        f"🔢 Serial kodi: <code>{code}</code>\n"
        f"➕ Yangi qismlar: <b>{num(count)} ta</b>\n"
        f"📺 Jami qismlar: <b>{num(total)} ta</b>"
    )


ASK_DELETE_CODE = "🗑 <b>O'chirmoqchi bo'lgan kino/serial kodini kiriting:</b>"
DELETE_NOT_FOUND = "❌ Bunday kodli kino topilmadi yoki allaqachon o'chirib yuborilgan!"
ASK_ONLY_NUMBER = "⚠️ Faqat raqam kiriting!"


def content_deleted(code: int) -> str:
    return f"✅ <b>{code}</b> kodli kontent o'chirildi!"


def ask_delete_episode(code: int, count: int, title: str) -> str:
    """Serial kodi kiritilganda — qism soni + qaysi qismni o'chirish so'rovi."""
    return (
        "╭── 🗑 <b>QISM O'CHIRISH</b> ──╮\n\n"
        f"📺 Serial: <b>{esc(title) or 'Nomsiz'}</b>\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"📺 Jami qismlar: <b>{num(count)} ta</b>\n"
        "╰────────────────────╯\n\n"
        f"🗑 <b>Nechanchi qismni o'chirmoqchisiz?</b>\n"
        f"Raqam kiriting <i>(1 – {count})</i>:\n\n"
        "<i>🧹 Butun serialni o'chirish uchun: 0</i>"
    )


def episode_not_exist(ep: int, count: int) -> str:
    return (
        f"❌ <b>{ep}-qism mavjud emas!</b>\n\n"
        f"📺 Bu serialda faqat <b>{num(count)} ta</b> qism bor.\n"
        "🔢 To'g'ri raqam kiriting:"
    )


def episode_deleted(ep: int, remaining: int) -> str:
    return (
        f"✅ <b>{ep}-qism</b> o'chirildi!\n"
        f"📺 Qolgan qismlar: <b>{num(remaining)} ta</b>\n\n"
        "🗑 Yana o'chirmoqchi bo'lsangiz — raqam kiriting,\n"
        "yoki «❌ Bekor qilish» tugmasini bosing."
    )


def episode_deleted_last(ep: int) -> str:
    return (
        f"✅ <b>{ep}-qism</b> o'chirildi!\n\n"
        "📭 Serialda boshqa qism qolmadi.\n"
        "<i>Yangi qism qo'shishingiz yoki serialni butunlay o'chirishingiz mumkin.</i>"
    )


def content_stats_text(s: dict, when: str) -> str:
    return (
        "╭── 📊 <b>KONTENT STATISTIKA</b> ──╮\n\n"
        f"🎬 Faol kinolar: <b>{num(s['movies'])}</b>\n"
        f"📺 Faol seriallar: <b>{num(s['series'])}</b>\n"
        f"🎞 Jami qismlar: <b>{num(s['episodes'])}</b>\n"
        f"🗑 O'chirilganlar: <b>{num(s['deleted'])}</b>\n"
        f"👁 Jami ko'rishlar: <b>{num(s['views'])}</b>\n\n"
        f"🕐 Yangilandi: {when}\n"
        "╰──────────────────────╯"
    )


def top_content_text(rows: list[dict]) -> str:
    if not rows:
        return "📭 Hali kontent qo'shilmagan!"
    medals = ("🥇", "🥈", "🥉")
    lines = ["╭── 🏆 <b>TOP 10 KONTENT</b> ──╮\n"]
    for i, row in enumerate(rows):
        mark = medals[i] if i < 3 else f"{i + 1}."
        icon = "🎬" if row["ctype"] == "movie" else "📺"
        raw = row["title"] or row["caption"].splitlines()[0]
        title = esc(raw)[:34]
        lines.append(f"{mark} {icon} <code>{row['code']}</code> · 👁 {num(row['views'])}\n"
                     f"     <i>{title}</i>")
    lines.append("\n╰────────────────────╯")
    return "\n".join(lines)


# ═══════════════════════════════════════════════════════
#                  KANAL SOZLAMALARI
# ═══════════════════════════════════════════════════════

CHANNEL_MENU = (
    "╭── 📡 <b>KANAL SOZLAMALARI</b> ──╮\n\n"
    "Bu bo'limda siz:\n"
    "📦 Baza kanal (kontent ombori)\n"
    "🔒 Majburiy obuna kanallari\n"
    "📩 Zayavka (so'rovnomali) kanallar\n"
    "    qo'shishingiz, ✏️ tahrirlashingiz\n"
    "    va 🗑 o'chirishingiz mumkin!\n"
    "╰──────────────────────╯"
)

BASE_CHANNEL_INFO = (
    "🔹 <b>1. Baza kanal</b>\n"
    "<i>Asosiy kontent kanali</i>\n\n"
    "• Kinolar va seriallar shu yerga joylanadi\n"
    "• Bot shu kanaldan foydalanuvchiga yuboradi\n\n"
    "➕ <b>Qo'shish:</b>\n"
    "① Kanal yarating\n"
    "② Botni Admin qiling\n"
    "③ @username yoki Kanal ID kiriting"
)

MANDATORY_CHANNEL_INFO = (
    "🔹 <b>2. Majburiy obuna kanali</b>\n"
    "<i>Obunasiz kino yo'q!</i>\n\n"
    "• Foydalanuvchi kino olishdan oldin\n"
    "  obuna bo'lishi shart\n"
    "• Bir nechta kanal qo'shish mumkin\n\n"
    "➕ <b>Qo'shish:</b>\n"
    "① Kanalni tanlang\n"
    "② Botni Admin qiling\n"
    "③ @username ni kiriting"
)

REQUEST_CHANNEL_INFO = (
    "🔹 <b>3. Zayavka kanal</b>\n"
    "<i>Private kanal — so'rov yetarli!</i>\n\n"
    "• Foydalanuvchi qo'shilish so'rovi yuboradi\n"
    "• So'rov yuborilishi bilan obuna hisoblanadi\n"
    "• (Ixtiyoriy) bot avtomatik qabul qiladi\n\n"
    "➕ <b>Qo'shish:</b>\n"
    "① Private kanal yarating\n"
    "② Botni Admin qiling («Invite users» huquqi bilan)\n"
    "③ Kanal ID (-100xxxxxxxxxx) kiriting"
)

ASK_CHANNEL = "🔗 <b>Kanal @username yoki ID sini yuboring:</b>"
ASK_CHANNEL_ID = "🔗 <b>Kanal ID sini yuboring</b> <i>(-100...)</i>:"
ASK_CHANNEL_TITLE = "✏️ <b>Obuna panelida ko'rinadigan nomni kiriting</b> <i>(masalan: Kanal-1)</i>:"

BASE_ADDED = "✅ Baza kanal muvaffaqiyatli qo'shildi!\nEndi kinolar shu kanalga yuklanadi 📦"
BASE_EXISTS = "⚠️ Baza kanal allaqachon mavjud! Avval eskisini o'chiring."
MANDATORY_ADDED = "✅ Majburiy obuna kanali qo'shildi!"
REQUEST_ADDED = "✅ Zayavka kanal qo'shildi!"
CHANNEL_DUPLICATE = "⚠️ Bu kanal allaqachon qo'shilgan!"


def channel_failed(reason: str) -> str:
    return f"❌ Kanal qo'shilmadi!\n<b>Sabab:</b> {esc(reason)}"


CHANNELS_EMPTY = "📭 Hali kanal mavjud emas!"
ASK_DELETE_SECTION = "🗑 <b>Qaysi kanalni o'chirmoqchisiz?</b> Bo'limni tanlang:"


# ─────────── ✏️ KANALNI TAHRIRLASH ───────────

CHANNEL_EDIT_SECTION = (
    "╭── ✏️ <b>KANALNI TAHRIRLASH</b> ──╮\n\n"
    "Qaysi bo'limdagi kanalni\n"
    "tahrirlamoqchisiz?\n\n"
    "📦 <b>Baza</b> — kontent ombori\n"
    "🔒 <b>Majburiy</b> — obuna kanallari\n"
    "📩 <b>Zayavka</b> — so'rovnomali kanallar\n"
    "╰──────────────────────╯\n\n"
    "👇 Bo'limni tanlang:"
)


def channel_edit_list(label: str, count: int) -> str:
    return (
        "╭── ✏️ <b>KANALNI TAHRIRLASH</b> ──╮\n\n"
        f"📂 Bo'lim: <b>{label}</b>\n"
        f"📡 Kanallar: <b>{count} ta</b>\n"
        "╰──────────────────────╯\n\n"
        "👇 Tahrirlamoqchi bo'lgan kanalni tanlang:"
    )


def channel_edit_card(
    title: str, username: str | None, label: str, chat_id: int, link: str | None,
    *, is_base: bool = False,
) -> str:
    uname = f"@{username}" if username else "— <i>(private kanal)</i>"
    link_line = f"📎 Havola: {esc(link)}\n" if (link and not username) else ""
    warn = (
        "\n⚠️ <i>Baza kanal almashtirilsa, eski kinolar\n"
        "zaxira usulda (file_id) yuboriladi.</i>\n"
        if is_base else ""
    )
    return (
        "╭── ✏️ <b>KANAL TAHRIRLASH</b> ──╮\n\n"
        f"📛 Nomi <i>(tugmada ko'rinadi)</i>: <b>{esc(title)}</b>\n"
        f"🔗 Username: {uname}\n"
        f"📂 Bo'lim: <b>{label}</b>\n"
        f"🆔 ID: <code>{chat_id}</code>\n"
        f"{link_line}"
        f"{warn}"
        "╰──────────────────────╯\n\n"
        "👇 <b>Nimani o'zgartirmoqchisiz?</b>"
    )


def ask_new_channel_title(current: str) -> str:
    return (
        "✏️ <b>Yangi nomni kiriting:</b>\n"
        f"<i>Joriy nom: {esc(current)}</i>\n\n"
        "<i>Bu nom obuna panelidagi tugmada ko'rinadi.</i>"
    )


ASK_NEW_CHANNEL_REF = (
    "🔗 <b>Yangi @username yoki kanal ID sini yuboring:</b>\n"
    "<i>(masalan: @kanalim yoki -1001234567890)</i>\n\n"
    "<i>⚠️ Bot yangi kanalda ham admin bo'lishi shart!</i>"
)

CHANNEL_TITLE_UPDATED = "✅ <b>Kanal nomi yangilandi!</b>"
CHANNEL_CHAT_UPDATED = "✅ <b>Kanal ma'lumotlari yangilandi!</b>"


def confirm_channel_delete(title: str, link: str) -> str:
    return (
        f"📡 Kanal: <b>{esc(title)}</b>\n"
        f"🔗 {esc(link)}\n\n"
        "❓ Rostdan ham bu kanalni\no'chirib tashlamoqchimisiz?"
    )


CHANNEL_DELETED = "✅ Kanal muvaffaqiyatli o'chirildi!"


def channel_stats_text(s: dict, when: str) -> str:
    return (
        "╭── 📊 <b>KANAL STATISTIKA</b> ──╮\n\n"
        f"📦 Baza kanal: <b>{s['base']} ta</b>\n"
        f"🔒 Majburiy kanallar: <b>{s['mandatory']} ta</b>\n"
        f"📩 Zayavka kanallar: <b>{s['request']} ta</b>\n\n"
        f"🕐 Yangilandi: {when}\n"
        "╰─────────────────────╯"
    )


# ═══════════════════════════════════════════════════════
#                  ADMIN SOZLAMALARI
# ═══════════════════════════════════════════════════════

ADMIN_MENU = (
    "╭── 👑 <b>ADMIN SOZLAMALARI</b> ──╮\n\n"
    "Bu bo'limda siz:\n"
    "➕ Yangi admin qo'shishingiz\n"
    "👥 Adminlar ro'yxatini ko'rishingiz\n"
    "🔐 Huquqlarni boshqarishingiz mumkin!\n"
    "╰──────────────────────╯"
)

ASK_ADMIN_ID = "🆔 <b>Yangi admin Telegram ID sini yuboring:</b>"
ADMIN_ADDED = "✅ Admin muvaffaqiyatli qo'shildi!"
ADMIN_USER_NOT_FOUND = "❌ Bu ID bilan foydalanuvchi botda topilmadi!"
ADMIN_ALREADY = "❌ Admin qo'shilmadi!\n<b>Sabab:</b> bu foydalanuvchi allaqachon admin."
ADMINS_EMPTY = "📭 Hali admin qo'shilmagan!"
CANNOT_DELETE_MAIN = "⛔️ Asosiy adminni o'chirib bo'lmaydi!"
CANNOT_DELETE_SELF = "⛔️ O'zingizni o'chira olmaysiz!"

NEW_ADMIN_GREETING = (
    "╭──────────────────╮\n"
    "   🎉 <b>TABRIKLAYMIZ!</b>\n"
    "╰──────────────────╯\n\n"
    "👑 Siz botga <b>admin</b> etib tayinlandingiz!\n"
    "🔐 Kirish: /admin buyrug'i orqali"
)

ADMIN_REMOVED_NOTICE = "⚠️ Siz asosiy admin tomonidan adminlik huquqidan olib tashlandingiz!"

PERM_LABELS = {
    "content": "🎬 Kino qo'shish",
    "channels": "📡 Kanal qo'shish",
    "admins": "👑 Admin qo'shish",
}


def admin_card(a: dict, username: str | None) -> str:
    badge = "👑 Asosiy admin" if a["role"] == "main" else "🟡 Yordamchi admin"
    mark = lambda v: "✅" if v else "❌"  # noqa: E731
    return (
        "╭── 👑 <b>ADMIN MA'LUMOTLARI</b> ──╮\n\n"
        f"👑 Turi: {badge}\n"
        f"🆔 ID: <code>{a['telegram_id']}</code>\n"
        f"🔗 Username: {('@' + username) if username else '—'}\n"
        f"📦 Holat: 🟢 Faol\n\n"
        "──── <b>HUQUQLAR</b> ────\n"
        f"🎬 Kino qo'shish: {mark(a['can_content'])}\n"
        f"📡 Kanal qo'shish: {mark(a['can_channels'])}\n"
        f"👑 Admin qo'shish: {mark(a['can_admins'])}\n"
        "╰──────────────────────╯"
    )


def confirm_admin_delete(tid: int) -> str:
    return f"❓ Rostdan ham <code>{tid}</code> ni adminlikdan olib tashlamoqchimisiz?"


ADMIN_DELETED = "✅ Admin muvaffaqiyatli o'chirildi!"


def perm_granted(perm: str) -> str:
    return f"🎉 Sizga «{PERM_LABELS[perm]}» huquqi berildi! ✅"


def perm_revoked(perm: str) -> str:
    return f"🔒 Sizdan «{PERM_LABELS[perm]}» huquqi olib tashlandi! ❌"


# ═══════════════════════════════════════════════════════
#                      BROADCAST
# ═══════════════════════════════════════════════════════

ASK_BROADCAST = (
    "✍️ <b>Foydalanuvchilarga yuboriladigan xabarni yuboring:</b>\n\n"
    "<i>Matn, rasm, video, GIF, stiker, voice, dumaloq video,\n"
    "hujjat, audio yoki forward — barchasi qabul qilinadi.</i>"
)

BROADCAST_PREVIEW = "👆 <b>Xabar shunday ko'rinadi.</b>\n\nYuborishni tasdiqlaysizmi?"
BROADCAST_NO_USERS = "📭 Hali foydalanuvchi yo'q!"


def broadcast_progress(sent: int, failed: int, percent: int) -> str:
    return (
        "📤 <b>Yuborilmoqda...</b>\n\n"
        f"✅ Yetkazildi: <b>{num(sent)}</b>\n"
        f"❌ Yetkazilmadi: <b>{num(failed)}</b>\n"
        f"⏳ Jarayon: <b>{percent}%</b>"
    )


def broadcast_done(total: int, sent: int, failed: int, elapsed: str) -> str:
    return (
        "╭── 📨 <b>XABAR YUBORILDI</b> ──╮\n\n"
        f"👥 Jami: <b>{num(total)}</b>\n"
        f"✅ Yetkazildi: <b>{num(sent)}</b>\n"
        f"❌ Yetkazilmadi: <b>{num(failed)}</b>\n"
        "   <i>(botni bloklaganlar)</i>\n"
        f"⏱ Vaqt: {elapsed}\n"
        "╰─────────────────────╯"
    )


# ═══════════════════════════════════════════════════════
#                    BILDIRISHNOMA
# ═══════════════════════════════════════════════════════

def notifications_panel(is_on: bool) -> str:
    state = "🟢 Yoniq" if is_on else "🔴 O'chiq"
    return (
        "╭── 🔔 <b>BILDIRISHNOMA</b> ──╮\n\n"
        f"Holat: <b>{state}</b>\n\n"
        "Yoqilganda:\n"
        "🟢 Yangi foydalanuvchi qo'shilsa\n"
        "🔴 Foydalanuvchi botni tark etsa\n"
        "   → sizga real vaqtda xabar keladi!\n"
        "╰───────────────────╯"
    )


# ═══════════════════════════════════════════════════════
#            KINO/SERIAL — BEPUL / PULLIK TANLASH
# ═══════════════════════════════════════════════════════

CHOOSE_MOVIE_TYPE = (
    "╭── ➕ <b>KINO QO'SHISH</b> ──╮\n\n"
    "Qanday kino qo'shmoqchisiz?\n\n"
    "🆓 <b>Bepul</b> — hamma bemalol ko'radi\n"
    "💎 <b>Pullik</b> — sotib olib yoki premium\n"
    "    obuna bilan ko'riladi\n"
    "╰───────────────────╯"
)

CHOOSE_SERIES_TYPE = (
    "╭── ➕ <b>SERIAL QO'SHISH</b> ──╮\n\n"
    "Qanday serial qo'shmoqchisiz?\n\n"
    "🆓 <b>Bepul</b> — hamma bemalol ko'radi\n"
    "💎 <b>Pullik</b> — bir marta sotib olib\n"
    "    barcha qismlar ochiladi\n"
    "╰────────────────────╯"
)

ASK_MOVIE_PRICE = (
    "💰 <b>Kinoni ko'rish (sotib olish) narxini kiriting:</b>\n"
    "<i>Faqat raqam, so'mda (masalan: 5000)</i>"
)
ASK_SERIES_PRICE = (
    "💰 <b>Serialni sotib olish narxini kiriting:</b>\n"
    "<i>Bu narx butun serial uchun — barcha qismlar ochiladi.</i>\n"
    "<i>Faqat raqam, so'mda (masalan: 15000)</i>"
)
NOT_A_PRICE = "⚠️ Faqat musbat raqam kiriting! <i>(masalan: 5000)</i>"


# ═══════════════════════════════════════════════════════
#              KINO/SERIAL TAVSIFINI TAHRIRLASH
# ═══════════════════════════════════════════════════════

EDIT_ASK_CODE = "✏️ <b>Tahrirlamoqchi bo'lgan kino/serial kodini kiriting:</b>"
EDIT_NOT_FOUND = "❌ Bunday kodli kino/serial topilmadi!"


def edit_current_caption(code: int, title: str, caption: str) -> str:
    return (
        "╭── ✏️ <b>TAVSIFNI TAHRIRLASH</b> ──╮\n\n"
        f"🔢 Kod: <code>{code}</code>\n"
        f"🎬 Nomi: <b>{esc(title) or 'Nomsiz'}</b>\n"
        "╰────────────────────╯\n\n"
        "📄 <b>Joriy tavsif</b> <i>(nusxa oling, tahrirlang va yuboring):</i>"
    )


EDIT_DONE = "✅ <b>Tavsif muvaffaqiyatli yangilandi!</b>"


# ═══════════════════════════════════════════════════════
#                  FOYDALANUVCHI MENYUSI
# ═══════════════════════════════════════════════════════

def balance_panel(name: str, username: str | None, tid: int, balance: int,
                  is_premium: bool, premium_left: str | None) -> str:
    uname = f"@{username}" if username else "No username"
    prem = (
        f"💎 Premium: <b>Faol</b> <i>({premium_left} qoldi)</i>"
        if is_premium else "💎 Premium: <b>Yo'q</b>"
    )
    return (
        "╭─────────────────────╮\n"
        "     👤 <b>MENING PROFILIM</b>\n"
        "╰─────────────────────╯\n\n"
        f"🙍 Ism: <b>{esc(name)}</b>\n"
        f"🔗 Username: {esc(uname)}\n"
        f"🆔 ID: <code>{tid}</code> <i>(nusxa olish uchun bosing)</i>\n"
        f"{DIVIDER}\n"
        f"💰 Balans: <b>{num(balance)} so'm</b>\n"
        f"{prem}\n"
        f"{DIVIDER}\n"
        "💳 Balansni to'ldirish uchun quyidagi tugmani bosing 👇"
    )


PREMIUM_BENEFITS = (
    "✅ Barcha <b>pullik</b> kino va seriallar\n"
    "✅ <b>Majburiy obunalarsiz</b> kino ko'rish\n"
    "✅ Kino/seriallarni <b>yuklab olish</b>\n"
    "✅ Do'stlarga <b>ulashish (forward)</b>\n"
    "✅ Har bir yangi kontentga birinchi kirish"
)


def premium_panel(prices: dict[str, int]) -> str:
    """Premium taklifi — faqat obunasi YO'Q foydalanuvchiga ko'rinadi."""
    return (
        "╭─────────────────────╮\n"
        "     💎 <b>PREMIUM OBUNA</b>\n"
        "╰─────────────────────╯\n\n"
        "Premium obuna nima beradi?\n\n"
        f"{PREMIUM_BENEFITS}\n\n"
        f"{DIVIDER}\n"
        "💵 <b>Tariflar:</b>\n"
        f"• 1 oy — <b>{num(prices['1m'])} so'm</b>\n"
        f"• 3 oy — <b>{num(prices['3m'])} so'm</b>\n"
        f"• 6 oy — <b>{num(prices['6m'])} so'm</b>\n"
        f"• 1 yil — <b>{num(prices['1y'])} so'm</b>\n"
        f"{DIVIDER}\n"
        "👇 Quyidan tarifni tanlang:"
    )


def premium_gate_panel(prices: dict[str, int]) -> str:
    """«💎 Obunasiz ko'rish» — majburiy obuna panelidan ochiladigan taklif."""
    return (
        "╭─────────────────────╮\n"
        "   👑 <b>OBUNASIZ KO'RISH</b>\n"
        "╰─────────────────────╯\n\n"
        "🔓 <b>Premium</b> obuna egalari uchun\n"
        "majburiy obuna <b>umuman yo'q</b>!\n\n"
        "🚫 Kanallarga obuna bo'lish shart emas\n"
        "⚡️ Kod yuborasiz — kino darhol keladi\n\n"
        f"{DIVIDER}\n"
        "🎁 <b>Yana nimalar ochiladi?</b>\n"
        f"{PREMIUM_BENEFITS}\n"
        f"{DIVIDER}\n"
        "💵 <b>Tariflar:</b>\n"
        f"• 1 oy — <b>{num(prices['1m'])} so'm</b>\n"
        f"• 3 oy — <b>{num(prices['3m'])} so'm</b>\n"
        f"• 6 oy — <b>{num(prices['6m'])} so'm</b>\n"
        f"• 1 yil — <b>{num(prices['1y'])} so'm</b>\n"
        f"{DIVIDER}\n"
        "👇 Quyidan tarifni tanlang:"
    )


def premium_active_panel(tariff_label: str, started: str, until: str, remaining: str) -> str:
    """Faol obunachi «💎 Premium obuna» ni bosganda — qayta sotib olish YO'Q,
    faqat chiroyli ma'lumot kartasi ko'rinadi."""
    return (
        "╭─────────────────────╮\n"
        "   👑 <b>SIZ — PREMIUM A'ZOSIZ!</b>\n"
        "╰─────────────────────╯\n\n"
        "🎉 Siz allaqachon <b>Premium obuna</b>\n"
        "sotib olgansiz — qayta sotib olish\n"
        "shart emas! 😌\n\n"
        f"{DIVIDER}\n"
        "🎫 <b>OBUNA MA'LUMOTLARI</b>\n"
        f"{DIVIDER}\n"
        f"📌 Tarif: <b>{tariff_label}</b>\n"
        f"🗓 Boshlangan: <b>{started}</b>\n"
        f"📅 Amal qiladi: <b>{until}</b> gacha\n"
        f"⏳ Qolgan muddat: <b>{remaining}</b>\n"
        f"{DIVIDER}\n"
        "🔓 <b>Sizga ochiq imkoniyatlar:</b>\n\n"
        f"{PREMIUM_BENEFITS}\n"
        f"{DIVIDER}\n"
        "✨ <i>Yoqimli tomosha tilaymiz!</i> ✨"
    )


def premium_confirm(tariff_label: str, price: int, balance: int) -> str:
    return (
        "╭── 💎 <b>TASDIQLASH</b> ──╮\n\n"
        f"🎫 Tarif: <b>{tariff_label}</b>\n"
        f"💰 Narxi: <b>{num(price)} so'm</b>\n"
        f"👛 Balansingiz: <b>{num(balance)} so'm</b>\n"
        "╰──────────────────╯\n\n"
        "❓ Rostdan ham premium obunani\nsotib olmoqchimisiz?"
    )


def premium_insufficient(price: int, balance: int) -> str:
    return (
        "╭── ⚠️ <b>MABLAG' YETARLI EMAS</b> ──╮\n\n"
        f"💰 Kerak: <b>{num(price)} so'm</b>\n"
        f"👛 Balansingiz: <b>{num(balance)} so'm</b>\n"
        f"➖ Yetishmaydi: <b>{num(price - balance)} so'm</b>\n"
        "╰──────────────────────╯\n\n"
        "💳 Avval balansingizni to'ldiring 👇"
    )


def premium_congrats(tariff_label: str, until: str) -> str:
    return (
        "╭─────────────────────╮\n"
        "      🎉 <b>TABRIKLAYMIZ!</b>\n"
        "╰─────────────────────╯\n\n"
        "💎 Siz <b>PREMIUM</b> obunachisiz!\n\n"
        f"🎫 Tarif: <b>{tariff_label}</b>\n"
        f"📅 Amal qiladi: <b>{until}</b> gacha\n\n"
        "🔓 Endi sizga ochiq:\n"
        f"{PREMIUM_BENEFITS}\n\n"
        f"{DIVIDER}\n"
        "✨ <i>Yoqimli tomosha tilaymiz!</i> ✨"
    )


def premium_expired_notice() -> str:
    return (
        "╭── 💎 <b>PREMIUM TUGADI</b> ──╮\n\n"
        "⏳ Premium obunangiz muddati tugadi.\n\n"
        "Pullik kontentdan yana bahramand bo'lish\n"
        "uchun obunani yangilang 👇\n"
        "╰──────────────────────╯"
    )


def premium_cancelled_notice() -> str:
    return (
        "╭── 💎 <b>OBUNA BEKOR QILINDI</b> ──╮\n\n"
        "⚠️ Premium obunangiz admin tomonidan\n"
        "bekor qilindi.\n\n"
        "Savollar bo'lsa «🆘 Yordam» orqali\n"
        "biz bilan bog'laning.\n"
        "╰──────────────────────╯"
    )


PREMIUM_ALREADY = "💎 Sizda allaqachon faol premium obuna bor!"


# ═══════════════════════════════════════════════════════
#                   BALANS TO'LDIRISH
# ═══════════════════════════════════════════════════════

NO_CARDS = (
    "⚠️ <b>Hozircha to'lov kartasi mavjud emas.</b>\n\n"
    "Iltimos, keyinroq urinib ko'ring yoki\n«🆘 Yordam» orqali admin bilan bog'laning."
)


def topup_intro(cards: list[dict]) -> str:
    lines = [
        "╭─────────────────────╮\n"
        "     💳 <b>BALANS TO'LDIRISH</b>\n"
        "╰─────────────────────╯\n",
        "Quyidagi kartaga o'tkazma qiling:\n",
    ]
    for c in cards:
        lines.append(
            f"{DIVIDER}\n"
            f"💳 <code>{esc(c['number'])}</code>\n"
            f"👤 {esc(c['holder'])}"
        )
    lines.append(
        f"\n{DIVIDER}\n"
        "📝 <b>To'lov tartibi:</b>\n"
        "① Yuqoridagi kartaga pul o'tkazing\n"
        "② Qancha to'lganingizni raqamda yozing\n"
        "③ To'lov chekini yuboring (rasm yoki PDF)\n"
        "④ Admin tasdiqlagach balansingiz to'ladi\n\n"
        "💰 <b>Qancha to'ldirmoqchisiz? Summani kiriting:</b>\n"
        "<i>(masalan: 20000)</i>"
    )
    return "\n".join(lines)


NOT_AN_AMOUNT = "⚠️ Faqat musbat raqam kiriting! <i>(masalan: 20000)</i>"
ASK_RECEIPT = (
    "🧾 <b>Endi to'lov chekini yuboring</b>\n"
    "<i>(rasm yoki PDF hujjat ko'rinishida)</i>"
)
NEED_RECEIPT = "⚠️ Iltimos, chekni <b>rasm</b> yoki <b>PDF</b> ko'rinishida yuboring!"


def topup_submitted(amount: int) -> str:
    return (
        "╭── ✅ <b>SO'ROV YUBORILDI</b> ──╮\n\n"
        f"💰 Summa: <b>{num(amount)} so'm</b>\n"
        "⏳ To'lovingiz admin tomonidan\n    tekshirilmoqda...\n\n"
        "Tasdiqlangach balansingiz avtomatik\nto'ldiriladi va sizga xabar keladi! 🔔\n"
        "╰──────────────────────╯"
    )


def payment_request_admin(name: str, username: str | None, tid: int, amount: int, when: str) -> str:
    uname = f"@{username}" if username else "No username"
    return (
        "╭── 💳 <b>YANGI TO'LOV SO'ROVI</b> ──╮\n\n"
        f"🙍 Ism: <b>{esc(name)}</b>\n"
        f"🔗 Username: {esc(uname)}\n"
        f"🆔 ID: <code>{tid}</code>\n"
        f"💰 Summa: <b>{num(amount)} so'm</b>\n"
        f"🕐 {when}\n"
        "╰──────────────────────╯\n\n"
        "👆 Chekni tekshiring va tasdiqlang:"
    )


def payment_approved_user(amount: int, balance: int) -> str:
    return (
        "╭── ✅ <b>TO'LOV TASDIQLANDI</b> ──╮\n\n"
        f"💰 To'ldirildi: <b>{num(amount)} so'm</b>\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>\n\n"
        "Xaridingiz uchun rahmat! 🎬\n"
        "╰──────────────────────╯"
    )


def payment_rejected_user(amount: int, reason: str) -> str:
    return (
        "╭── ❌ <b>TO'LOV RAD ETILDI</b> ──╮\n\n"
        f"💰 Summa: <b>{num(amount)} so'm</b>\n\n"
        "📝 <b>Sabab:</b>\n"
        f"<i>{esc(reason)}</i>\n"
        "╰──────────────────────╯\n\n"
        "Savol bo'lsa «🆘 Yordam» orqali murojaat qiling."
    )


ASK_REJECT_REASON = "📝 <b>Rad etish sababini kiriting:</b>\n<i>(foydalanuvchiga yuboriladi)</i>"
PAYMENT_ALREADY_HANDLED = "⚠️ Bu so'rov allaqachon ko'rib chiqilgan!"
PAYMENT_APPROVED_ADMIN = "✅ To'lov tasdiqlandi, balans to'ldirildi!"
PAYMENT_REJECTED_ADMIN = "❌ To'lov rad etildi, foydalanuvchiga xabar berildi."


# ═══════════════════════════════════════════════════════
#                  PULLIK KONTENT SOTIB OLISH
# ═══════════════════════════════════════════════════════

def purchase_success(title: str, price: int, balance: int) -> str:
    return (
        "╭── ✅ <b>SOTIB OLINDI</b> ──╮\n\n"
        f"🎬 <b>{esc(title) or 'Kontent'}</b>\n"
        f"💰 To'landi: <b>{num(price)} so'm</b>\n"
        f"👛 Qolgan balans: <b>{num(balance)} so'm</b>\n"
        "╰──────────────────╯\n\n"
        "🎉 Endi bu kontentni istalgan vaqtda\nqayta ko'ra olasiz!"
    )


PURCHASE_NEED_ACCESS = "🔒 Bu pullik kontent! Avval sotib oling yoki premium obuna bo'ling."


# ═══════════════════════════════════════════════════════
#              YORDAM (ADMIN BILAN ALOQA)
# ═══════════════════════════════════════════════════════

def help_panel(remaining: int, limit: int, reset_left: str | None) -> str:
    if remaining > 0:
        limit_line = f"✍️ Bugun yozishingiz mumkin: <b>{remaining}/{limit} ta</b>"
        if reset_left:
            limit_line += f"\n♻️ Limit tiklanadi: <b>{reset_left}</b> dan so'ng"
    else:
        limit_line = (
            "🚫 Xabar limiti tugadi!\n"
            f"♻️ Qayta yozish: <b>{reset_left}</b> dan so'ng"
        )
    return (
        "╭── 🆘 <b>YORDAM / ALOQA</b> ──╮\n\n"
        "Savol yoki muammoyingiz bormi?\n"
        "Adminlarga xabar yozing — tez orada\n"
        "javob beramiz! 💬\n"
        f"{DIVIDER}\n"
        f"{limit_line}\n"
        "╰────────────────────╯\n\n"
        "👇 Xabaringizni shu yerga yozing:"
    )


def help_limit_reached(reset_left: str) -> str:
    return (
        "🚫 <b>Xabar limiti tugadi!</b>\n\n"
        f"♻️ Qayta yozishingiz mumkin bo'ladi:\n<b>{reset_left}</b> dan so'ng."
    )


def help_message_sent(remaining: int, limit: int) -> str:
    return (
        "✅ <b>Xabaringiz adminlarga yuborildi!</b>\n"
        "Tez orada javob beramiz. 💬\n\n"
        f"✍️ Qolgan xabarlar: <b>{remaining}/{limit} ta</b>"
    )


def help_message_admin(name: str, username: str | None, tid: int) -> str:
    uname = f"@{username}" if username else "No username"
    return (
        "╭── 🆘 <b>YORDAM XABARI</b> ──╮\n\n"
        f"🙍 Ism: <b>{esc(name)}</b>\n"
        f"🔗 Username: {esc(uname)}\n"
        f"🆔 ID: <code>{tid}</code>\n"
        "╰────────────────────╯\n\n"
        "💬 <b>Xabar:</b>"
    )


# ═══════════════════════════════════════════════════════
#              ADMIN — PREMIUM OBUNACHILAR
# ═══════════════════════════════════════════════════════

PREMIUM_SUBS_EMPTY = "📭 Hozircha faol premium obunachi yo'q!"


def premium_subs_header(count: int) -> str:
    return (
        "╭── 💎 <b>PREMIUM OBUNACHILAR</b> ──╮\n\n"
        f"📋 Jami faol: <b>{count} ta</b>\n\n"
        "<i>Ma'lumot uchun ID ni bosing 👇</i>\n"
        "╰──────────────────────╯"
    )


def premium_sub_card(name: str, username: str | None, tid: int, tariff_label: str,
                     until: str, remaining: str) -> str:
    uname = f"@{username}" if username else "No username"
    return (
        "╭── 💎 <b>PREMIUM OBUNACHI</b> ──╮\n\n"
        f"🙍 Ism: <b>{esc(name)}</b>\n"
        f"🔗 Username: {esc(uname)}\n"
        f"🆔 ID: <code>{tid}</code>\n"
        f"{DIVIDER}\n"
        f"🎫 Tarif: <b>{tariff_label}</b>\n"
        f"📅 Tugaydi: <b>{until}</b>\n"
        f"⏳ Qolgan muddat: <b>{remaining}</b>\n"
        "╰──────────────────────╯"
    )


def confirm_cancel_premium(name: str) -> str:
    return (
        f"❓ Rostdan ham <b>{esc(name)}</b> ning\n"
        "premium obunasini bekor qilmoqchimisiz?"
    )


PREMIUM_CANCELLED_ADMIN = "✅ Premium obuna bekor qilindi!"


# ═══════════════════════════════════════════════════════
#                    ADMIN — SOZLAMALAR
# ═══════════════════════════════════════════════════════

SETTINGS_MENU = (
    "╭── ⚙️ <b>SOZLAMALAR</b> ──╮\n\n"
    "Bu bo'limda siz:\n"
    "💳 To'lov kartalarini boshqarasiz\n"
    "💎 Premium tarif narxlarini belgilaysiz\n"
    "🆘 Yordam xabar limitini sozlaysiz\n"
    "╰────────────────────╯"
)


def cards_panel(cards: list[dict]) -> str:
    if not cards:
        body = "📭 Hali karta qo'shilmagan."
    else:
        rows = []
        for c in cards:
            rows.append(f"💳 <code>{esc(c['number'])}</code>\n👤 {esc(c['holder'])}")
        body = f"\n{DIVIDER}\n".join(rows)
    return (
        "╭── 💳 <b>TO'LOV KARTALARI</b> ──╮\n\n"
        f"{body}\n"
        "╰──────────────────────╯"
    )


ASK_CARD_NUMBER = "💳 <b>Karta raqamini kiriting:</b>\n<i>(masalan: 8600 1234 5678 9012)</i>"
ASK_CARD_HOLDER = "👤 <b>Karta egasining ism-familiyasini kiriting:</b>"
CARD_ADDED = "✅ Karta muvaffaqiyatli qo'shildi!"
CARD_UPDATED = "✅ Karta ma'lumotlari yangilandi!"
CARD_DELETED = "✅ Karta o'chirildi!"
CARDS_EMPTY = "📭 Hali karta qo'shilmagan!"


def confirm_card_delete(number: str, holder: str) -> str:
    return (
        f"💳 Karta: <code>{esc(number)}</code>\n"
        f"👤 Egasi: {esc(holder)}\n\n"
        "❓ Rostdan ham bu kartani o'chirmoqchimisiz?"
    )


def tariffs_panel(prices: dict[str, int]) -> str:
    return (
        "╭── 💎 <b>PREMIUM TARIFLARI</b> ──╮\n\n"
        f"🎫 1 oy — <b>{num(prices['1m'])} so'm</b>\n"
        f"🎫 3 oy — <b>{num(prices['3m'])} so'm</b>\n"
        f"🎫 6 oy — <b>{num(prices['6m'])} so'm</b>\n"
        f"🎫 1 yil — <b>{num(prices['1y'])} so'm</b>\n"
        "╰──────────────────────╯\n\n"
        "👇 O'zgartirmoqchi bo'lgan tarifni tanlang:"
    )


def ask_tariff_price(tariff_label: str) -> str:
    return (
        f"💰 <b>«{tariff_label}» tarifi narxini kiriting:</b>\n"
        "<i>Faqat raqam, so'mda (masalan: 25000)</i>"
    )


TARIFF_UPDATED = "✅ Tarif narxi yangilandi!"


def help_limit_panel(limit: int) -> str:
    return (
        "╭── 🆘 <b>YORDAM LIMITI</b> ──╮\n\n"
        f"✍️ Hozirgi limit: <b>{limit} ta / 12 soat</b>\n\n"
        "<i>Foydalanuvchi 12 soat ichida nechta\nxabar yubora olishini belgilaydi.</i>\n"
        "╰──────────────────────╯"
    )


ASK_HELP_LIMIT = "✍️ <b>Yangi limitni kiriting</b> <i>(12 soatlik, masalan: 5)</i>:"
HELP_LIMIT_UPDATED = "✅ Yordam limiti yangilandi!"


# ═══════════════════════════════════════════════════════
#                    👥 REFERAL DASTURI
# ═══════════════════════════════════════════════════════

def referral_panel(link: str, price: int, count: int, earned: int) -> str:
    return (
        "╭─────────────────────╮\n"
        "     👥 <b>REFERAL DASTURI</b>\n"
        "╰─────────────────────╯\n\n"
        "Do'stlaringizni taklif qiling va\npul ishlang! 💸\n\n"
        "📌 <b>Qanday ishlaydi?</b>\n"
        "① Quyidagi havolangizni ulashing\n"
        "② Do'stingiz havola orqali botga kirsin\n"
        "③ Barcha kanallarga obuna bo'lsin\n"
        "④ Hisobingizga avtomatik pul tushadi!\n"
        f"{DIVIDER}\n"
        f"💰 Har bir do'st uchun: <b>{num(price)} so'm</b>\n"
        f"{DIVIDER}\n"
        "📊 <b>Sizning natijangiz:</b>\n"
        f"👤 Takliflar: <b>{num(count)} ta</b>\n"
        f"💵 Ishlangan: <b>{num(earned)} so'm</b>\n"
        f"{DIVIDER}\n"
        "🔗 <b>Sizning havolangiz</b> <i>(nusxa olish uchun bosing):</i>\n"
        f"<code>{esc(link)}</code>"
    )


def referral_reward(reward: int, balance: int) -> str:
    return (
        "╭── 🎉 <b>YANGI REFERAL!</b> ──╮\n\n"
        "Do'stingiz havolangiz orqali kirib,\n"
        "barcha kanallarga obuna bo'ldi! 🥳\n\n"
        f"💰 Hisobingizga: <b>+{num(reward)} so'm</b>\n"
        f"👛 Yangi balans: <b>{num(balance)} so'm</b>\n"
        "╰──────────────────────╯\n\n"
        "Yana taklif qiling — yana ishlang! 💸"
    )


def referral_settings_panel(price: int) -> str:
    return (
        "╭── 👥 <b>REFERAL NARXI</b> ──╮\n\n"
        f"💰 Har bir referal uchun: <b>{num(price)} so'm</b>\n\n"
        "<i>Do'st taklif qilgan foydalanuvchiga, do'sti\n"
        "barcha kanallarga obuna bo'lgach, shu summa\n"
        "avtomatik qo'shiladi.</i>\n"
        "╰──────────────────────╯"
    )


ASK_REFERRAL_PRICE = (
    "💰 <b>Har bir referal uchun mukofot summasini kiriting:</b>\n"
    "<i>Faqat raqam, so'mda (masalan: 1000). 0 — referalni o'chiradi.</i>"
)
REFERRAL_PRICE_UPDATED = "✅ Referal narxi yangilandi!"
