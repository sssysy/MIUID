from PIL import Image

from gsuid_core.bot import Bot
from gsuid_core.help.utils import register_help
from gsuid_core.models import Event
from gsuid_core.sv import SV, get_plugin_available_prefix

from .get_help import ICON, get_help

sv_miuid_help = SV("MIUID 帮助")


@sv_miuid_help.on_fullmatch("帮助", block=True)
async def send_help(bot: Bot, ev: Event) -> None:
    await bot.send(await get_help(ev.user_pm))


register_help(
    "MIUID",
    f"{get_plugin_available_prefix('MIUID')}帮助",
    Image.open(ICON),
)
