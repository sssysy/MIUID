"""米家设备命令的业务处理。"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.api.mijia_client import (
    MIJIA_CLIENTS,
    MijiaAuthError,
    MijiaClientError,
    MijiaDeviceAmbiguousError,
    MijiaDeviceControlError,
    MijiaDeviceInfo,
    MijiaDeviceNotFoundError,
    MijiaDeviceSession,
)
from ..utils.database.model_mijia_user import MijiaUser


def _command_body(ev: Event, keyword: str) -> str:
    text = ev.raw_text.strip()
    for prefix in ("mi", "MI"):
        if text.startswith(prefix):
            text = text[len(prefix) :].lstrip()
            break
    if text.startswith(keyword):
        return text[len(keyword) :].lstrip()
    return text


async def _session(ev: Event) -> tuple[str, str, str]:
    row = await MijiaUser.get_default(ev.user_id)
    if row is None:
        raise MijiaAuthError("当前没有默认米家账号，请先使用 mi登录")
    return ev.user_id, row.mijia_user_id, row.auth_json


async def _persist_auth(
    session: MijiaDeviceSession,
    user_id: str,
    mijia_user_id: str,
    previous_auth_json: str,
) -> None:
    auth_json = await session.read_auth_json()
    if auth_json != previous_auth_json:
        await MijiaUser.save_auth(
            user_id=user_id,
            mijia_user_id=mijia_user_id,
            auth_json=auth_json,
        )
        session.accept_auth_json(auth_json)


def _format_device(device: MijiaDeviceInfo) -> str:
    location = " / ".join(part for part in (device["home_name"], device["room_name"]) if part)
    online = "未知" if device["is_online"] is None else ("在线" if device["is_online"] else "离线")
    return f"{device['name']}（{location or '未知位置'}，{online}）"


async def list_devices(bot: Bot, ev: Event) -> None:
    try:
        user_id, mijia_user_id, auth_json = await _session(ev)
        session = await MIJIA_CLIENTS.get(user_id, mijia_user_id, auth_json)
        devices = await session.list_devices(refresh=True)
        await _persist_auth(session, user_id, mijia_user_id, auth_json)
    except MijiaAuthError as exc:
        await bot.send(str(exc))
        return
    except MijiaClientError as exc:
        await bot.send(str(exc))
        return

    if not devices:
        await bot.send("当前米家账号没有可用设备")
        return
    lines = [f"共 {len(devices)} 台设备："]
    for index, device in enumerate(devices, start=1):
        lines.append(f"{index}. {_format_device(device)}")
    await bot.send("\n".join(lines))


async def inspect_device(bot: Bot, ev: Event) -> None:
    query = _command_body(ev, "查看").strip()
    if not query:
        await bot.send("请发送：mi查看 设备名")
        return
    try:
        user_id, mijia_user_id, auth_json = await _session(ev)
        session = await MIJIA_CLIENTS.get(user_id, mijia_user_id, auth_json)
        device, capabilities, status = await session.inspect_device(query)
        await _persist_auth(session, user_id, mijia_user_id, auth_json)
    except (MijiaAuthError, MijiaDeviceNotFoundError, MijiaDeviceAmbiguousError) as exc:
        await bot.send(str(exc))
        return
    except MijiaClientError as exc:
        await bot.send(str(exc))
        return

    lines = [f"{_format_device(device)}", "实时状态："]
    if status:
        lines.extend(f"- {name}：{value}" for name, value in status.items())
    else:
        lines.append("- 无可读取状态")
    lines.append("可用操作：")
    for item in capabilities:
        flags = []
        if item["readable"]:
            flags.append("可读")
        if item["writable"]:
            flags.append("可写")
        if item["kind"] == "action":
            flags.append("动作")
        suffix = f"（{'，'.join(flags)}）" if flags else ""
        values = f"；可选：{'，'.join(item['values'])}" if item["values"] else ""
        lines.append(f"- {item['name']}：{item['description']}{suffix}{values}")
    if not capabilities:
        lines.append("- 该设备没有公开的 MIoT 属性或动作")
    await bot.send("\n".join(lines))


async def execute(bot: Bot, ev: Event) -> None:
    try:
        user_id, mijia_user_id, auth_json = await _session(ev)
        session = await MIJIA_CLIENTS.get(user_id, mijia_user_id, auth_json)
        device, kind, name, value = await session.execute(
            _command_body(ev, "执行")
        )
        await _persist_auth(session, user_id, mijia_user_id, auth_json)
    except (MijiaAuthError, MijiaDeviceNotFoundError, MijiaDeviceAmbiguousError) as exc:
        await bot.send(str(exc))
        return
    except MijiaDeviceControlError as exc:
        await bot.send(str(exc))
        return
    except MijiaClientError as exc:
        await bot.send(str(exc))
        return
    if kind == "power":
        await bot.send(f"已{'开启' if value == '开' else '关闭'} {device['name']}")
    elif kind == "property":
        await bot.send(f"已设置 {device['name']} 的 {name} 为 {value}")
    else:
        await bot.send(f"已执行 {device['name']} 的动作 {name}")
