"""FSM holatlari — har bir jarayonda «❌ Bekor qilish» mavjud."""

from aiogram.fsm.state import State, StatesGroup


class AuthSG(StatesGroup):
    password = State()


class ContentSG(StatesGroup):
    """Kino VA serial qo'shish uchun umumiy oqim (ctype FSM data'da saqlanadi).

    Qadamlar: nomi → janr → yil → davomiyligi → tili → trailer →
              (kino: to'liq video)  yoki  (serial: qismlar) → (pulli: narx).
    """

    title = State()
    genre = State()
    year = State()
    duration = State()
    language = State()
    trailer = State()
    movie_file = State()   # faqat kino: to'liq film
    episodes = State()     # faqat serial: qismlar
    price = State()        # faqat pulli: sotib olish narxi


class EditContentSG(StatesGroup):
    """Kino/serial tavsifini tahrirlash."""

    code = State()
    caption = State()


class EpisodeSG(StatesGroup):
    """Mavjud serialga qism qo'shish (nom/trailer qayta so'ralmaydi)."""

    code = State()
    episodes = State()


class DeleteSG(StatesGroup):
    code = State()
    episode = State()   # serial uchun: qaysi qismni o'chirish


class ChannelSG(StatesGroup):
    chat = State()
    title = State()


class ChannelEditSG(StatesGroup):
    """Mavjud kanalni tahrirlash: nom yoki username/ID (row_id FSM data'da)."""

    title = State()   # obuna panelidagi tugmada ko'rinadigan nom
    chat = State()    # yangi @username yoki -100... ID


class AdminSG(StatesGroup):
    new_id = State()


class BanSG(StatesGroup):
    minutes = State()


class UserSearchSG(StatesGroup):
    """Admin: foydalanuvchini Telegram ID orqali izlash."""

    query = State()


class BalanceSG(StatesGroup):
    """Admin: foydalanuvchi balansini to'ldirish / balansdan ayirish."""

    amount = State()   # data: target (telegram_id), op ('add' | 'sub')


class BroadcastSG(StatesGroup):
    message = State()
    confirm = State()


# ═══════════════════════════════════════════════════════
#          PULLIK KONTENT / BALANS / PREMIUM / YORDAM
# ═══════════════════════════════════════════════════════

class TopUpSG(StatesGroup):
    """Foydalanuvchi balans to'ldirish: summa → chek (rasm/PDF)."""

    amount = State()
    receipt = State()


class RejectSG(StatesGroup):
    """Admin to'lovni rad etganda — sabab."""

    reason = State()


class HelpSG(StatesGroup):
    """Foydalanuvchi admin bilan aloqa — xabar yozish."""

    message = State()


class CardSG(StatesGroup):
    """Admin karta qo'shish / tahrirlash: raqam → egasi."""

    number = State()
    holder = State()


class SettingsSG(StatesGroup):
    """Admin sozlamalari: tarif narxlari, yordam limiti, referal narxi."""

    tariff = State()
    help_limit = State()
    referral = State()
