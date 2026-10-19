"""Admin routerlari — ULANISH TARTIBI MUHIM.

panel.py birinchi: /admin va parol FSM'i boshqa hamma narsadan oldin ushlanadi.
"""

from aiogram import Router

from handlers.admin import (
    admins,
    broadcast,
    channels,
    content_mgmt,
    notifications,
    panel,
    premium,
    settings,
    statistics,
)

router = Router(name="admin")
router.include_routers(
    panel.router,
    statistics.router,
    content_mgmt.router,
    channels.router,
    admins.router,
    broadcast.router,
    notifications.router,
    premium.router,
    settings.router,
)
