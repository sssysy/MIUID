"""米家设备命令的业务处理。"""

from gsuid_core.bot import Bot
from gsuid_core.models import Event

from ..utils.api.mijia_client import (
    MIJIA_CLIENTS,
    MijiaAuthError,
    MijiaCapability,
    MijiaClientError,
    MijiaDeviceAmbiguousError,
    MijiaDeviceControlError,
    MijiaDeviceInfo,
    MijiaDeviceNotFoundError,
    MijiaDeviceSession,
    MijiaStatusInfo,
)
from ..utils.database.model_mijia_user import MijiaUser
from ..utils.maps import (
    HIDDEN_PROPERTIES,
    display_property_name,
    display_value_option,
    format_status_value,
    split_property_name,
)


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


def _group_capabilities(
    capabilities: list[MijiaCapability],
) -> list[tuple[str, list[MijiaCapability]]]:
    channels: dict[int, list[MijiaCapability]] = {}
    general: list[MijiaCapability] = []
    for item in capabilities:
        base, channel = split_property_name(item["name"])
        if base in HIDDEN_PROPERTIES:
            continue
        if channel is None:
            general.append(item)
        else:
            channels.setdefault(channel, []).append(item)

    groups = [(f"第 {channel} 路", items) for channel, items in sorted(channels.items())]
    if general:
        groups.append(("其他" if channels else "", general))
    return groups


def _capability_label(item: MijiaCapability) -> str:
    base, channel = split_property_name(item["name"])
    if channel is not None:
        return display_property_name(base, item["description"])
    return display_property_name(item["name"], item["description"])


def _capability_suffix(item: MijiaCapability) -> str:
    if item["kind"] == "action":
        return "（动作）"
    if not item["writable"]:
        return "（只读）"
    return ""


def _append_capability(lines: list[str], item: MijiaCapability) -> None:
    name = _capability_label(item)
    lines.append(f"  {name}{_capability_suffix(item)}")
    if item["value_type"] == "bool":
        return
    for option in item["values"]:
        lines.append(f"    {display_value_option(option['value'], option['label'])}")


def _format_device_detail(
    user_id: str,
    device: MijiaDeviceInfo,
    capabilities: list[MijiaCapability],
    status: dict[str, MijiaStatusInfo],
) -> str:
    parts = [part for part in (device["home_name"], device["room_name"]) if part]
    location = " / ".join(parts)
    online = "未知" if device["is_online"] is None else ("在线" if device["is_online"] else "离线")
    lines = [
        f"@{user_id} 查看设备：{device['name']}",
        f"{location or '未知位置'} · {online}",
        "",
        "-= 实时状态 =-",
    ]
    visible_status = [
        (name, info) for name, info in status.items() if split_property_name(name)[0] not in HIDDEN_PROPERTIES
    ]
    if visible_status:
        for name, info in visible_status:
            lines.append(f"- {display_property_name(name)}：{_format_status(name, info)}")
    else:
        lines.append("- 无可读取状态")

    lines.extend(["", "-= 可用操作 =-"])
    if not capabilities:
        lines.append("- 该设备没有公开的 MIoT 属性或动作")
    for group_label, items in _group_capabilities(capabilities):
        if group_label:
            lines.append(f"[{group_label}]")
        for item in items:
            _append_capability(lines, item)
    return "\n".join(lines)


def _format_status(name: str, info: MijiaStatusInfo) -> str:
    options = [(option["value"], option["label"]) for option in info["value_options"]]
    return format_status_value(
        name,
        info["value"],
        info["value_type"],
        options,
    )


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

    groups: dict[str, list[MijiaDeviceInfo]] = {}
    for device in devices:
        parts = [part for part in (device["home_name"], device["room_name"]) if part]
        location = " - ".join(parts) if parts else "未知位置"
        groups.setdefault(location, []).append(device)

    lines = [f"@{ev.user_id} 你的米家设备列表："]
    index = 1
    for location, group in groups.items():
        online = [d for d in group if d["is_online"] is True]
        offline = [d for d in group if d["is_online"] is not True]
        lines.append("")
        lines.append(f"[{location}]")
        if online:
            lines.append("-= 在线 =-")
            for device in online:
                lines.append(f"{index}. {device['name']}")
                index += 1
        if offline:
            lines.append("-= 离线 =-")
            for device in offline:
                lines.append(f"{index}. {device['name']}")
                index += 1
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

    await bot.send(_format_device_detail(ev.user_id, device, capabilities, status))


async def execute(bot: Bot, ev: Event) -> None:
    try:
        user_id, mijia_user_id, auth_json = await _session(ev)
        session = await MIJIA_CLIENTS.get(user_id, mijia_user_id, auth_json)
        device, kind, name, value = await session.execute(_command_body(ev, "执行"))
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
