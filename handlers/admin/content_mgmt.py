"""🎬 Kino/serial qo'shish (qadamma-qadam + trailer), o'chirish, statistika."""

from __future__ import annotations

import contextlib
import logging
from typing import Any

from aiogram import Bot, F, Router
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.filters import StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message

from database import queries as q
from keyboards.admin_kb import (
    BTN_CONTENT,
    back_content_kb,
    cancel_kb,
    content_menu_kb,
    content_stats_kb,
    content_type_kb,
    finish_kb,
)
from states.admin_states import ContentSG, DeleteSG, EditContentSG, EpisodeSG
from utils import texts
from utils.filters import HasPerm, IsAdmin
from utils.helpers import hhmm

log = logging.getLogger(__name__)
router = Router(name="admin:content")
router.message.filter(IsAdmin())
router.callback_query.filter(IsAdmin())


async def _base_ready(bot: Bot) -> str | None:
    """Baza kanal shartlari. None → hammasi joyida, aks holda xato matni."""
    base = q.base_channel()
    if base is None:
        return texts.NO_BASE_CHANNEL
    try:
        me = await bot.get_chat_member(base["chat_id"], bot.id)
    except TelegramAPIError:
        return texts.BOT_NOT_ADMIN_BASE
    if me.status not in {"administrator", "creator"}:
        return texts.BOT_NOT_ADMIN_BASE
    return None


async def _post_media(bot: Bot, chat_id: int, mtype: str, file_id: str, caption: str):
    """Trailer (video yoki rasm) ni baza kanalga joylaydi."""
    if mtype == "photo":
        return await bot.send_photo(chat_id, file_id, caption=caption)
    return await bot.send_video(chat_id, file_id, caption=caption)


@router.message(F.text == BTN_CONTENT)
async def content_menu(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        texts.CONTENT_MENU,
        reply_markup=content_menu_kb(q.has_perm(message.from_user.id, "content")),
    )


@router.callback_query(F.data == "c:back")
async def back_to_menu(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(
            texts.CONTENT_MENU,
            reply_markup=content_menu_kb(q.has_perm(call.from_user.id, "content")),
        )
    await call.answer()


# ═══════════════════════════════════════════════════════
#        QADAMMA-QADAM TAVSIF (kino + serial umumiy)
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "c:add_movie", HasPerm("content"))
async def add_movie_choose(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.CHOOSE_MOVIE_TYPE, reply_markup=content_type_kb("movie"))
    await call.answer()


@router.callback_query(F.data == "c:add_series", HasPerm("content"))
async def add_series_choose(call: CallbackQuery, state: FSMContext):
    await state.clear()
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(texts.CHOOSE_SERIES_TYPE, reply_markup=content_type_kb("series"))
    await call.answer()


@router.callback_query(F.data.in_({"c:addm:free", "c:addm:paid"}), HasPerm("content"))
async def add_movie_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    error = await _base_ready(bot)
    if error:
        await call.message.answer(error)
        await call.answer()
        return
    is_paid = call.data.endswith(":paid")
    await state.set_state(ContentSG.title)
    await state.update_data(ctype="movie", is_paid=is_paid)
    await call.message.answer(
        f"{texts.ADD_MOVIE_HEADER}\n\n{texts.ASK_TITLE}", reply_markup=cancel_kb()
    )
    await call.answer()


@router.callback_query(F.data.in_({"c:adds:free", "c:adds:paid"}), HasPerm("content"))
async def add_series_start(call: CallbackQuery, state: FSMContext, bot: Bot):
    error = await _base_ready(bot)
    if error:
        await call.message.answer(error)
        await call.answer()
        return
    is_paid = call.data.endswith(":paid")
    await state.set_state(ContentSG.title)
    await state.update_data(ctype="series", is_paid=is_paid)
    await call.message.answer(
        f"{texts.ADD_SERIES_HEADER}\n\n{texts.ASK_TITLE}", reply_markup=cancel_kb()
    )
    await call.answer()


# ─── nomi → janr → yil → davomiyligi → tili (matn qadamlari) ───

@router.message(ContentSG.title, F.text)
async def step_title(message: Message, state: FSMContext):
    await state.update_data(title=message.text.strip())
    await state.set_state(ContentSG.genre)
    await message.answer(texts.ASK_GENRE, reply_markup=cancel_kb())


@router.message(ContentSG.genre, F.text)
async def step_genre(message: Message, state: FSMContext):
    await state.update_data(genre=message.text.strip())
    await state.set_state(ContentSG.year)
    await message.answer(texts.ASK_YEAR, reply_markup=cancel_kb())


@router.message(ContentSG.year, F.text)
async def step_year(message: Message, state: FSMContext):
    await state.update_data(year=message.text.strip())
    await state.set_state(ContentSG.duration)
    await message.answer(texts.ASK_DURATION, reply_markup=cancel_kb())


@router.message(ContentSG.duration, F.text)
async def step_duration(message: Message, state: FSMContext):
    await state.update_data(duration=message.text.strip())
    await state.set_state(ContentSG.language)
    await message.answer(texts.ASK_LANGUAGE, reply_markup=cancel_kb())


@router.message(ContentSG.language, F.text)
async def step_language(message: Message, state: FSMContext):
    await state.update_data(language=message.text.strip())
    await state.set_state(ContentSG.trailer)
    await message.answer(texts.ASK_TRAILER, reply_markup=cancel_kb())


# Matn kutilgan qadamlarda matn kelmasa — bitta umumiy ogohlantirish.
@router.message(
    StateFilter(
        ContentSG.title, ContentSG.genre, ContentSG.year,
        ContentSG.duration, ContentSG.language,
    )
)
async def step_need_text(message: Message):
    await message.answer(texts.NEED_TEXT)


# ─── trailer (video yoki rasm — majburiy) ───

@router.message(ContentSG.trailer, F.photo | F.video)
async def step_trailer(message: Message, state: FSMContext):
    if message.photo:
        ttype, tfid = "photo", message.photo[-1].file_id
    else:
        ttype, tfid = "video", message.video.file_id
    await state.update_data(trailer_type=ttype, trailer_file_id=tfid)

    data = await state.get_data()
    if data["ctype"] == "movie":
        await state.set_state(ContentSG.movie_file)
        await message.answer(texts.ASK_MOVIE_FILE, reply_markup=cancel_kb())
    else:
        await state.update_data(episodes=[])
        await state.set_state(ContentSG.episodes)
        await message.answer(texts.ASK_FIRST_EPISODE, reply_markup=finish_kb())


@router.message(ContentSG.trailer)
async def step_trailer_invalid(message: Message):
    await message.answer(texts.NEED_MEDIA)


# ─── kino: to'liq film ───

@router.message(ContentSG.movie_file, F.video)
async def step_movie_file(message: Message, state: FSMContext, bot: Bot):
    await state.update_data(film_file_id=message.video.file_id)
    data = await state.get_data()

    # Pullik kino → oxirida narx so'raymiz.
    if data.get("is_paid"):
        await state.set_state(ContentSG.price)
        await message.answer(texts.ASK_MOVIE_PRICE, reply_markup=cancel_kb())
        return

    await state.clear()
    code = await _finalize_movie(data, bot, message.from_user.id)
    await message.answer(texts.movie_added(code, hhmm(), await _username(bot)))


@router.message(ContentSG.movie_file)
async def step_movie_file_invalid(message: Message):
    await message.answer(texts.NEED_VIDEO)


# ─── narx (faqat pullik kino/serial) ───

@router.message(ContentSG.price, F.text)
async def step_price(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip().replace(" ", "")
    if not raw.isdigit() or int(raw) <= 0:
        await message.answer(texts.NOT_A_PRICE)
        return

    price = int(raw)
    data = await state.get_data()
    await state.clear()

    if data["ctype"] == "movie":
        code = await _finalize_movie(data, bot, message.from_user.id, is_paid=True, price=price)
        await message.answer(
            texts.movie_added(code, hhmm(), await _username(bot), True, price)
        )
    else:
        await message.answer("⏳ Baza kanalga joylanmoqda...")
        code, added = await _finalize_series(
            data, bot, message.from_user.id, is_paid=True, price=price
        )
        await message.answer(texts.series_added(code, added, True, price))


@router.message(ContentSG.price)
async def step_price_invalid(message: Message):
    await message.answer(texts.NOT_A_PRICE)


# ─── serial: qismlar ───

@router.message(ContentSG.episodes, F.video)
async def step_episode(message: Message, state: FSMContext):
    data = await state.get_data()
    episodes: list[str] = data.get("episodes", [])
    episodes.append(message.video.file_id)
    await state.update_data(episodes=episodes)
    await message.answer(texts.episode_added(len(episodes)), reply_markup=finish_kb())


@router.message(ContentSG.episodes)
async def step_episode_invalid(message: Message):
    await message.answer(texts.NEED_VIDEO, reply_markup=finish_kb())


@router.callback_query(F.data == "c:finish", ContentSG.episodes)
async def series_finish(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    episodes: list[str] = data.get("episodes", [])
    if not episodes:
        await call.answer(texts.NEED_ONE_EPISODE, show_alert=True)
        return

    # Pullik serial → oxirida narx so'raymiz (qismlar FSM'da saqlangan).
    if data.get("is_paid"):
        await state.set_state(ContentSG.price)
        await call.message.answer(texts.ASK_SERIES_PRICE, reply_markup=cancel_kb())
        await call.answer()
        return

    await state.clear()
    await call.answer("⏳ Baza kanalga joylanmoqda...")
    code, added = await _finalize_series(data, bot, call.from_user.id)
    await call.message.answer(texts.series_added(code, added))


# ═══════════════════════════════════════════════════════
#                    YAKUNLASH (baza kanal)
# ═══════════════════════════════════════════════════════

async def _username(bot: Bot) -> str:
    return (await bot.me()).username or "PremiumKinoBot"


async def _finalize_movie(
    data: dict[str, Any], bot: Bot, added_by: int, *, is_paid: bool = False, price: int = 0
) -> int:
    base = q.base_channel()
    code = await q.next_code()
    username = await _username(bot)

    body = texts.content_body(
        data["title"], data["genre"], data["year"], data["duration"], data["language"],
        icon="🎬",
    )
    # Trailer'ni baza kanalga to'liq caption bilan joylaymiz (arxiv + zaxira).
    trailer_msg = await _post_media(
        bot, base["chat_id"], data["trailer_type"], data["trailer_file_id"],
        texts.movie_card(body, code, username),
    )
    # To'liq filmni baza kanalga joylaymiz.
    film_msg = await bot.send_video(
        base["chat_id"], data["film_file_id"],
        caption=texts.movie_watch_caption(data["title"], code, username),
    )

    await q.create_content(
        code, "movie",
        title=data["title"], caption=body,
        trailer_file_id=data["trailer_file_id"], trailer_type=data["trailer_type"],
        trailer_msg_id=trailer_msg.message_id,
        file_id=data["film_file_id"], base_msg_id=film_msg.message_id,
        is_paid=is_paid, price=price,
        added_by=added_by,
    )
    return code


async def _finalize_series(
    data: dict[str, Any], bot: Bot, added_by: int, *, is_paid: bool = False, price: int = 0
) -> tuple[int, int]:
    base = q.base_channel()
    code = await q.next_code()
    username = await _username(bot)
    episodes: list[str] = data["episodes"]

    body = texts.content_body(
        data["title"], data["genre"], data["year"], data["duration"], data["language"],
        icon="📺",
    )
    trailer_msg = await _post_media(
        bot, base["chat_id"], data["trailer_type"], data["trailer_file_id"],
        texts.series_card(body, code, username, len(episodes)),
    )

    await q.create_content(
        code, "series",
        title=data["title"], caption=body,
        trailer_file_id=data["trailer_file_id"], trailer_type=data["trailer_type"],
        trailer_msg_id=trailer_msg.message_id,
        is_paid=is_paid, price=price,
        added_by=added_by,
    )
    added = await _upload_episodes(
        bot, base["chat_id"], code, episodes, 1, username, data["title"]
    )
    return code, added


async def _upload_episodes(
    bot: Bot,
    base_chat: int,
    code: int,
    file_ids: list[str],
    start_from: int,
    username: str,
    title: str,
) -> int:
    """Qismlarni baza kanalga KETMA-KET joylaydi (flood bo'lmasin) va bazaga yozadi."""
    added = 0
    for offset, file_id in enumerate(file_ids):
        ep = start_from + offset
        try:
            posted = await bot.send_video(
                chat_id=base_chat,
                video=file_id,
                caption=texts.episode_caption(title, code, ep, username),
            )
            msg_id = posted.message_id
        except TelegramAPIError as e:
            log.error("Qism %s joylanmadi: %s", ep, e)
            msg_id = None
        await q.add_episode(code, ep, file_id, msg_id)
        added += 1
    return added


# ═══════════════════════════════════════════════════════
#              🎞 SERIALGA QISM QO'SHISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "c:add_ep", HasPerm("content"))
async def ask_series_code(call: CallbackQuery, state: FSMContext, bot: Bot):
    error = await _base_ready(bot)
    if error:
        await call.message.answer(error)
        await call.answer()
        return
    await state.set_state(EpisodeSG.code)
    await call.message.answer(texts.ASK_SERIES_CODE, reply_markup=cancel_kb())
    await call.answer()


@router.message(EpisodeSG.code, F.text)
async def got_series_code(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(texts.SERIES_NOT_FOUND)
        return

    code = int(raw)
    content = await q.get_content(code)
    if content is None or content["ctype"] != "series":
        await message.answer(texts.SERIES_NOT_FOUND)
        return

    last = await q.last_episode_number(code)
    await state.update_data(code=code, last=last, title=content["title"] or "", episodes=[])
    await state.set_state(EpisodeSG.episodes)
    await message.answer(
        f"📺 Serial topildi! Hozirgi qismlar: <b>{last} ta</b>\n\n"
        f"📥 <b>{last + 1}-qismni yuboring:</b>",
        reply_markup=finish_kb(),
    )


@router.message(EpisodeSG.episodes, F.video)
async def append_episode(message: Message, state: FSMContext):
    data = await state.get_data()
    episodes: list[str] = data.get("episodes", [])
    episodes.append(message.video.file_id)
    await state.update_data(episodes=episodes)
    await message.answer(
        texts.episode_added(data["last"] + len(episodes)), reply_markup=finish_kb()
    )


@router.message(EpisodeSG.episodes)
async def append_episode_invalid(message: Message):
    await message.answer(texts.NEED_VIDEO, reply_markup=finish_kb())


@router.callback_query(F.data == "c:finish", EpisodeSG.episodes)
async def append_finish(call: CallbackQuery, state: FSMContext, bot: Bot):
    data = await state.get_data()
    episodes: list[str] = data.get("episodes", [])
    if not episodes:
        await call.answer(texts.NEED_ONE_EPISODE, show_alert=True)
        return

    await state.clear()
    await call.answer("⏳ Baza kanalga joylanmoqda...")

    code, last = data["code"], data["last"]
    base = q.base_channel()
    username = await _username(bot)

    added = await _upload_episodes(
        bot, base["chat_id"], code, episodes, last + 1, username, data["title"]
    )
    await call.message.answer(texts.episodes_appended(code, added, last + added))


# ═══════════════════════════════════════════════════════
#                 🗑 KONTENT O'CHIRISH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "c:del", HasPerm("content"))
async def ask_delete(call: CallbackQuery, state: FSMContext):
    await state.set_state(DeleteSG.code)
    await call.message.answer(texts.ASK_DELETE_CODE, reply_markup=cancel_kb())
    await call.answer()


@router.message(DeleteSG.code, F.text)
async def do_delete_code(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(texts.DELETE_NOT_FOUND)
        return

    code = int(raw)
    content = await q.get_content(code)
    if content is None:
        await message.answer(texts.DELETE_NOT_FOUND)
        return

    # Kino → butunlay o'chiriladi (avvalgidek).
    if content["ctype"] == "movie":
        await state.clear()
        await _delete_whole(bot, content, code)
        await message.answer(texts.content_deleted(code), reply_markup=back_content_kb())
        return

    # Serial → qism sonini ko'rsatib, qaysi qismni o'chirishni so'raymiz.
    episodes = await q.get_episodes(code)
    if not episodes:
        # Qismsiz serial — o'chiradigan qism yo'q, butunlay olib tashlaymiz.
        await state.clear()
        await _delete_whole(bot, content, code)
        await message.answer(texts.content_deleted(code), reply_markup=back_content_kb())
        return

    await state.update_data(code=code)
    await state.set_state(DeleteSG.episode)
    await message.answer(
        texts.ask_delete_episode(code, len(episodes), content["title"] or ""),
        reply_markup=cancel_kb(),
    )


@router.message(DeleteSG.episode, F.text)
async def do_delete_episode(message: Message, state: FSMContext, bot: Bot):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(texts.ASK_ONLY_NUMBER)
        return

    data = await state.get_data()
    code = data["code"]
    content = await q.get_content(code)
    if content is None:
        await state.clear()
        await message.answer(texts.DELETE_NOT_FOUND, reply_markup=back_content_kb())
        return

    ep = int(raw)

    # 0 → butun serialni o'chirish.
    if ep == 0:
        await state.clear()
        await _delete_whole(bot, content, code)
        await message.answer(texts.content_deleted(code), reply_markup=back_content_kb())
        return

    found, base_msg = await q.delete_episode(code, ep)
    if not found:
        count = await q.episode_count(code)
        await message.answer(texts.episode_not_exist(ep, count))
        return

    # Baza kanaldagi o'sha qism xabarini o'chiramiz.
    base = q.base_channel()
    if base and base_msg:
        await _delete_from_base(bot, base["chat_id"], [base_msg])

    remaining = await q.episode_count(code)
    if remaining == 0:
        await state.clear()
        await message.answer(texts.episode_deleted_last(ep), reply_markup=back_content_kb())
    else:
        # Holatni saqlaymiz — admin ketma-ket bir nechta qism o'chira olsin.
        await message.answer(texts.episode_deleted(ep, remaining), reply_markup=cancel_kb())


async def _delete_whole(bot: Bot, content: dict, code: int) -> None:
    """Kino yoki serialni butunlay o'chiradi (trailer + film / barcha qismlar)."""
    base = q.base_channel()
    msg_ids: list[int] = []
    if content["trailer_msg_id"]:
        msg_ids.append(content["trailer_msg_id"])
    if content["ctype"] == "movie":
        if content["base_msg_id"]:
            msg_ids.append(content["base_msg_id"])
    else:
        msg_ids += [e["base_msg_id"] for e in await q.get_episodes(code) if e["base_msg_id"]]

    if base and msg_ids:
        await _delete_from_base(bot, base["chat_id"], msg_ids)

    # Soft delete — kod abadiy band qoladi, boshqa kontentga berilmaydi.
    await q.delete_content(code)


async def _delete_from_base(bot: Bot, chat_id: int, msg_ids: list[int]) -> None:
    """delete_messages — 100 tagacha xabarni BITTA so'rovda o'chiradi."""
    for i in range(0, len(msg_ids), 100):
        batch = msg_ids[i : i + 100]
        try:
            await bot.delete_messages(chat_id, batch)
        except TelegramAPIError as e:
            log.warning("Baza kanaldan o'chirishda xato: %s", e)


# ═══════════════════════════════════════════════════════
#              ✏️ TAVSIFNI TAHRIRLASH
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data == "c:edit", HasPerm("content"))
async def ask_edit_code(call: CallbackQuery, state: FSMContext):
    await state.set_state(EditContentSG.code)
    await call.message.answer(texts.EDIT_ASK_CODE, reply_markup=cancel_kb())
    await call.answer()


@router.message(EditContentSG.code, F.text)
async def got_edit_code(message: Message, state: FSMContext):
    raw = message.text.strip()
    if not raw.isdigit():
        await message.answer(texts.EDIT_NOT_FOUND)
        return

    code = int(raw)
    content = await q.get_content(code)
    if content is None:
        await message.answer(texts.EDIT_NOT_FOUND)
        return

    await state.update_data(code=code)
    await state.set_state(EditContentSG.caption)
    await message.answer(
        texts.edit_current_caption(code, content["title"] or "", content["caption"]),
        reply_markup=cancel_kb(),
    )
    # Joriy tavsifni XOM ko'rinishda yuboramiz — admin nusxa olib, tahrirlab qaytaradi.
    await message.answer(content["caption"], parse_mode=None)


@router.message(EditContentSG.caption, F.text)
async def do_edit_caption(message: Message, state: FSMContext):
    data = await state.get_data()
    code = data["code"]
    await state.clear()
    ok = await q.update_content_caption(code, message.text)
    await message.answer(
        texts.EDIT_DONE if ok else texts.EDIT_NOT_FOUND, reply_markup=back_content_kb()
    )


@router.message(EditContentSG.caption)
async def edit_caption_invalid(message: Message):
    await message.answer(texts.NEED_TEXT)


# ═══════════════════════════════════════════════════════
#                📊 KONTENT STATISTIKA
# ═══════════════════════════════════════════════════════

@router.callback_query(F.data.in_({"c:stats", "c:stats_refresh"}))
async def content_stats(call: CallbackQuery):
    text = texts.content_stats_text(await q.content_stats(), hhmm())
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(text, reply_markup=content_stats_kb())
    await call.answer("🔄 Yangilandi" if call.data == "c:stats_refresh" else None)


@router.callback_query(F.data == "c:top")
async def top_content(call: CallbackQuery):
    text = texts.top_content_text(await q.top_content(10))
    with contextlib.suppress(TelegramBadRequest):
        await call.message.edit_text(text, reply_markup=content_stats_kb())
    await call.answer()
