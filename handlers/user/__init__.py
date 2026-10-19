"""Foydalanuvchi routerlari va middleware'lar.

MUHIM: `/start` obuna middleware'iga TUSHMAYDI.
Sababi — TZ §7.1 tartibi: avval foydalanuvchi bazaga yoziladi va adminlarga
🟢 bildirishnoma ketadi, KEYIN obuna tekshiriladi. Agar middleware /start ni
to'sib qo'ysa, obunasiz odam umuman ro'yxatdan o'tmay qolardi.
`start.py` obunani o'zi tekshirib, panelni ko'rsatadi.

Kontent (kod yuborish, qism olish) esa to'liq himoyalangan.
"""

from aiogram import Router

from handlers.user import content, menu, payments, start, subscription
from middlewares.ban_check import BanCheckMiddleware
from middlewares.subscription import SubscriptionMiddleware

router = Router(name="user")

# Bloklash — foydalanuvchi qismidagi HAMMA narsaga taalluqli.
router.message.middleware(BanCheckMiddleware())
router.callback_query.middleware(BanCheckMiddleware())

router.include_router(start.router)
router.include_router(subscription.router)

# Obuna to'sig'i — kontent, menyu, to'lov uchun.
gated = Router(name="user:gated")
gated.message.middleware(SubscriptionMiddleware())
gated.callback_query.middleware(SubscriptionMiddleware())
# TARTIB MUHIM: menyu tugmalari (Balans/Premium/Yordam) va to'lov jarayoni
# content.py dagi umumiy «raqam emas» to'sig'idan OLDIN tekshirilishi shart.
gated.include_router(menu.router)
gated.include_router(payments.router)
gated.include_router(content.router)

router.include_router(gated)
