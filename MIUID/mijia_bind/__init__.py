"""米家账号绑定命令。"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV

from .bind_services import login, logout, view

sv = SV("米家账号绑定", area="ALL")


@sv.on_fullmatch("登录", block=True)
async def mijia_login(bot: Bot, ev: Event) -> None:
    await login(bot, ev)


@sv.on_fullmatch("登出", block=True)
async def mijia_logout(bot: Bot, ev: Event) -> None:
    await logout(bot, ev)


@sv.on_fullmatch("查看", block=True)
async def mijia_view(bot: Bot, ev: Event) -> None:
    await view(bot, ev)
