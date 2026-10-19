"""Kod qabul qilish → trailer + tavsif → kino/serial yuborish.

TRAFIK TEJASH
─────────────
Media (trailer, to'liq film, qismlar) HECH QACHON qayta yuklanmaydi. Bot baza
kanaldagi xabarni `copy_message` bilan ko'chiradi — bu Telegram serveridagi
ichki amal, fayl bot orqali o'tmaydi (0 bayt trafik).
Zaxira yo'l: `file_id` (video yoki rasm — turiga qarab).

OQIM
────
  • Kino kodi   → trailer (video/rasm) + tavsif + «▶️ Kinoni ko'rish» tugmasi
                  tugma bosilsa → to'liq film keladi
  • Serial kodi → trailer (video/rasm) + tavsif + qism tugmalari (column 2)
                  qism bosilsa → o'sha qism videosi keladi
"""

from __future__ import annotations

import contextlib
import logging

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from config import config
from database import queries as q
from keyboards.user_kb import movie_watch_kb, paid_movie_kb, paid_series_kb, series_kb
from utils import texts

log = logging.getLogger(__name__)
router = Router(name="user:content")


async def _bot_username(bot: Bot) -> str:
    # aiogram `bot.me()` natijani keshlaydi → faqat bir marta API so'rovi.
    return (await bot.me()).username or "PremiumKinoBot"


async def _protect_for(tid: int) -> bool:
    """Kontent himoyasi qoidasi:

    🆓 Bepul tarif  → protect_content=True  (yuklab olish/forward YOPIQ)
    💎 Premium      → protect_content=False (yuklab olish/forward OCHIQ)
    👑 Adminlar     → himoyasiz (test/boshqaruv qulayligi uchun)
    """
    if q.is_admin(tid):
        return False
    return not await q.is_premium(tid)


async def _copy_or_send(
    bot: Bot,
    chat_id: int,
    media_msg_id: int | None,
    file_id: str | None,
    mtype: str | None,
    caption: str,
    reply_markup=None,
    protect: bool | None = None,
) -> bool:
    """Avval copy_message (tez, trafiksiz), bo'lmasa file_id bilan (turiga qarab).

    `protect=None` → config.protect_content (zaxira). Odatda barcha chaqiruvlar
    `_protect_for()` natijasini beradi: bepul tarif — himoyalangan (yuklab
    olish/forward yopiq), premium — ochiq.
    """
    prot = config.protect_content if protect is None else protect
    base = q.base_channel()
    if base and media_msg_id:
        try:
            await bot.copy_message(
                chat_id=chat_id,
                from_chat_id=base["chat_id"],
                message_id=media_msg_id,
                caption=caption,
                reply_markup=reply_markup,
                protect_content=prot,
            )
            return True
        except TelegramAPIError as e:
            log.warning("copy_message ishlamadi (msg %s): %s — file_id bilan urinamiz",
                        media_msg_id, e)

    if file_id:
        try:
            if mtype == "photo":
                await bot.send_photo(
                    chat_id, file_id, caption=caption, reply_markup=reply_markup,
                    protect_content=prot,
                )
            else:
                await bot.send_video(
                    chat_id, file_id, caption=caption, reply_markup=reply_markup,
                    protect_content=prot,
                )
            return True
        except TelegramAPIError as e:
            log.error("file_id bilan ham yuborib bo'lmadi: %s", e)
    return False


async def deliver(message: Message, bot: Bot, code: int) -> bool:
    """Kod bo'yicha trailer + tavsif kartasini yuboradi. False → topilmadi."""
    content = await q.get_content(code)
    if content is None:
        return False

    username = await _bot_username(bot)
    tid = message.from_user.id
    paid = bool(content["is_paid"])
    access = True if not paid else await q.has_access(tid, content)
    protect = await _protect_for(tid)

    if content["ctype"] == "movie":
        q.bump_views(code)  # buferga — diskka darhol yozilmaydi
        if access:
            caption = texts.movie_card(content["caption"], code, username)
            kb = movie_watch_kb(code)
        else:
            # Pullik, hali sotib olinmagan → narx + sotib olish tugmasi.
            caption = texts.paid_movie_card(content["caption"], code, username, content["price"])
            balance = await q.get_balance(tid)
            kb = paid_movie_kb(code, content["price"], balance >= content["price"])
        ok = await _copy_or_send(
            bot, message.chat.id,
            content["trailer_msg_id"], content["trailer_file_id"], content["trailer_type"],
            caption, reply_markup=kb, protect=protect,
        )
        if not ok:
            await message.answer(texts.MOVIE_NOT_FOUND)
        return True

    # ─────────── SERIAL ───────────
    episodes = await q.get_episodes(code)
    if not episodes:
        await message.answer(texts.MOVIE_NOT_FOUND)
        return True

    q.bump_views(code)
    ep_numbers = [e["ep_number"] for e in episodes]
    if access:
        caption = texts.series_card(content["caption"], code, username, len(episodes))
        kb = series_kb(code, 1, ep_numbers)
    else:
        caption = texts.paid_series_card(
            content["caption"], code, username, len(episodes), content["price"]
        )
        balance = await q.get_balance(tid)
        kb = paid_series_kb(code, content["price"], balance >= content["price"])
    ok = await _copy_or_send(
        bot, message.chat.id,
        content["trailer_msg_id"], content["trailer_file_id"], content["trailer_type"],
        caption, reply_markup=kb, protect=protect,
    )
    if not ok:
        await message.answer(texts.MOVIE_NOT_FOUND)
    return True


@router.message(F.text.regexp(r"^\d+$"))
async def by_code(message: Message, bot: Bot):
    """Faqat raqamdan iborat matn = kod."""
    q.touch_user(message.from_user.id)  # buferga
    if not await deliver(message, bot, int(message.text)):
        await message.answer(texts.MOVIE_NOT_FOUND)


@router.callback_query(F.data.startswith("watch:"))
async def watch_movie(call: CallbackQuery, bot: Bot):
    """«▶️ Kinoni ko'rish» → to'liq film alohida xabar bo'lib keladi."""
    code = int(call.data.split(":")[1])
    content = await q.get_content(code)
    if content is None or content["ctype"] != "movie":
        await call.answer("❌ Kino topilmadi!", show_alert=True)
        return

    # Pullik kino — kirish huquqi tekshiriladi.
    if content["is_paid"] and not await q.has_access(call.from_user.id, content):
        await call.answer(texts.PURCHASE_NEED_ACCESS, show_alert=True)
        return

    await call.answer("📥 Kino yuborilmoqda...")
    protect = await _protect_for(call.from_user.id)
    username = await _bot_username(bot)
    caption = texts.movie_watch_caption(content["title"] or "", code, username)
    ok = await _copy_or_send(
        bot,
        call.message.chat.id,
        content["base_msg_id"],
        content["file_id"],
        "video",
        caption,
        protect=protect,
    )
    if not ok:
        await call.message.answer("❌ Kinoni yuborib bo'lmadi. Keyinroq urinib ko'ring.")


# ═══════════════════════════════════════════════════════
#              💳 PULLIK KONTENT SOTIB OLISH
# ═══════════════════════════════════════════════════════

async def _deliver_after_purchase(call: CallbackQuery, bot: Bot, content: dict) -> None:
    """Sotib olingandan keyin: kino → film, serial → qism tugmalari."""
    tid = call.from_user.id
    code = content["code"]
    protect = await _protect_for(tid)
    username = await _bot_username(bot)

    if content["ctype"] == "movie":
        caption = texts.movie_watch_caption(content["title"] or "", code, username)
        ok = await _copy_or_send(
            bot, call.message.chat.id,
            content["base_msg_id"], content["file_id"], "video",
            caption, protect=protect,
        )
        if not ok:
            await call.message.answer("❌ Kinoni yuborib bo'lmadi. Keyinroq urinib ko'ring.")
        # Trailer kartasidagi tugmani «Kinoni ko'rish» ga o'zgartiramiz.
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_reply_markup(reply_markup=movie_watch_kb(code))
    else:
        episodes = await q.get_episodes(code)
        if not episodes:
            await call.message.answer(texts.MOVIE_NOT_FOUND)
            return
        ep_numbers = [e["ep_number"] for e in episodes]
        with contextlib.suppress(TelegramBadRequest):
            await call.message.edit_reply_markup(reply_markup=series_kb(code, 1, ep_numbers))
        await call.message.answer("👇 <b>Qismni tanlang:</b>", reply_markup=series_kb(code, 1, ep_numbers))


@router.callback_query(F.data.startswith("buypay:"))
async def buy_pay(call: CallbackQuery, bot: Bot):
    """Balans yetarli — narx yechiladi, sotib olinadi va kontent yuboriladi."""
    code = int(call.data.split(":")[1])
    content = await q.get_content(code)
    if content is None or not content["is_paid"]:
        await call.answer("❌ Kontent topilmadi!", show_alert=True)
        return

    tid = call.from_user.id
    price = int(content["price"])

    if not await q.has_access(tid, content):
        # Sotib olishni QULF sifatida ishlatamiz: ikki marta tez bosilsa ham
        # faqat bittasi True oladi → balansdan ikki marta yechilmaydi.
        newly = await q.add_purchase(tid, code, price)
        if newly:
            if not await q.deduct_balance(tid, price):
                # Balans yetmadi — sotib olishni bekor qilamiz.
                await q.remove_purchase(tid, code)
                await call.answer("❌ Mablag' yetarli emas!", show_alert=True)
                return
            balance = await q.get_balance(tid)
            await call.message.answer(
                texts.purchase_success(content["title"] or "", price, balance)
            )

    await call.answer("📥 Yuborilmoqda...")
    await _deliver_after_purchase(call, bot, content)


@router.callback_query(F.data.startswith("buyup:"))
async def buy_topup(call: CallbackQuery, state: FSMContext, bot: Bot):
    """Balans yetmaydi — «Sotib olish» → hisob to'ldirish bo'limi (yangi context)."""
    from handlers.user.payments import open_topup

    with contextlib.suppress(TelegramBadRequest):
        await call.message.delete()
    await open_topup(bot, call.message.chat.id, state)
    await call.answer()


@router.callback_query(F.data.startswith("ser:"))
async def series_page(call: CallbackQuery):
    """Sahifa almashish — faqat klaviatura EDIT qilinadi (yangi xabar yo'q)."""
    _, raw_code, raw_page = call.data.split(":")
    code, page = int(raw_code), int(raw_page)

    episodes = await q.get_episodes(code)
    if not episodes:
        await call.answer(texts.MOVIE_NOT_FOUND, show_alert=True)
        return

    pages = -(-len(episodes) // config.episodes_per_page)
    if page < 1:
        await call.answer("⚠️ Bu birinchi sahifa!", show_alert=True)
        return
    if page > pages:
        await call.answer("⚠️ Bu oxirgi sahifa!", show_alert=True)
        return

    ep_numbers = [e["ep_number"] for e in episodes]
    await call.message.edit_reply_markup(reply_markup=series_kb(code, page, ep_numbers))
    await call.answer()


@router.callback_query(F.data.startswith("ep:"))
async def send_episode(call: CallbackQuery, bot: Bot):
    """Qism alohida xabar bo'lib keladi — panel joyida qoladi."""
    _, raw_code, raw_ep = call.data.split(":")
    code, ep_number = int(raw_code), int(raw_ep)

    content = await q.get_content(code)
    episodes = await q.get_episodes(code)
    episode = next((e for e in episodes if e["ep_number"] == ep_number), None)
    if episode is None or content is None:
        await call.answer("❌ Bu qism topilmadi!", show_alert=True)
        return

    # Pullik serial — kirish huquqi tekshiriladi (sotib olingan / premium).
    if content["is_paid"] and not await q.has_access(call.from_user.id, content):
        await call.answer(texts.PURCHASE_NEED_ACCESS, show_alert=True)
        return

    await call.answer(f"📥 {ep_number}-qism yuborilmoqda...")
    protect = await _protect_for(call.from_user.id)
    username = await _bot_username(bot)
    ok = await _copy_or_send(
        bot,
        call.message.chat.id,
        episode["base_msg_id"],
        episode["file_id"],
        "video",
        texts.episode_caption(content["title"] or "", code, ep_number, username),
        protect=protect,
    )
    if not ok:
        await call.message.answer("❌ Qismni yuborib bo'lmadi. Keyinroq urinib ko'ring.")


@router.message(F.text)
async def not_a_code(message: Message):
    """Oxirgi to'siq: raqam bo'lmagan matn (admin routerlaridan keyin ulanadi)."""
    q.touch_user(message.from_user.id)
    await message.answer(texts.NOT_A_NUMBER)
