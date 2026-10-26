"""米家设备列表、查看与控制命令。"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event
from gsuid_core.sv import SV

from .device_services import execute, inspect_device, list_devices

sv = SV("米家设备控制", area="ALL")


@sv.on_fullmatch("设备列表", block=True)
async def mijia_device_list(bot: Bot, ev: Event) -> None:
    await list_devices(bot, ev)


@sv.on_prefix("查看", block=True)
async def mijia_device_inspect(bot: Bot, ev: Event) -> None:
    await inspect_device(bot, ev)


@sv.on_prefix("执行", block=True)
async def mijia_device_action(bot: Bot, ev: Event) -> None:
    await execute(bot, ev)
