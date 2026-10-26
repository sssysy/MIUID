"""米家同步 API 的异步访问边界。"""

import asyncio
import tempfile
from pathlib import Path
from typing import TypedDict

from mijiaAPI import DeviceGetError, DeviceSetError, LoginError, get_device_info, mijiaAPI
from mijiaAPI.devices import DevAction, DevProp

from gsuid_core.logger import logger


class MijiaClientError(Exception):
    """米家设备访问失败。"""


class MijiaAuthError(MijiaClientError):
    """米家登录凭据不可用。"""


class MijiaDeviceNotFoundError(MijiaClientError):
    """未找到唯一匹配的设备。"""


class MijiaDeviceAmbiguousError(MijiaClientError):
    """设备名称匹配到多个设备。"""


class MijiaDeviceControlError(MijiaClientError):
    """设备拒绝属性或动作操作。"""


class MijiaDeviceInfo(TypedDict):
    did: str
    name: str
    model: str
    spec_type: str
    home_id: str
    home_name: str
    room_id: str
    room_name: str
    is_online: bool | None


class MijiaCapability(TypedDict):
    name: str
    description: str
    kind: str
    readable: bool
    writable: bool
    values: list[str]


class MijiaDeviceSession:
    """单个米家账号的同步 SDK 会话，所有调用都在线程中串行执行。"""

    def __init__(self, auth_json: str) -> None:
        self._auth_json = auth_json
        self._source_auth_json = auth_json
        self._lock = asyncio.Lock()
        self._temp_dir: tempfile.TemporaryDirectory[str] | None = None
        self._api: mijiaAPI | None = None
        self._devices: list[MijiaDeviceInfo] | None = None
        self._devices_task: asyncio.Task[list[MijiaDeviceInfo]] | None = None
        self._specs: dict[str, dict[str, object]] = {}

    async def list_devices(self, *, refresh: bool = False) -> list[MijiaDeviceInfo]:
        async with self._lock:
            try:
                self._devices = await self._refresh_devices_locked(force=refresh)
                return list(self._devices)
            except MijiaClientError:
                raise
            except Exception as exc:
                logger.exception("[米家] 获取设备列表失败")
                raise MijiaClientError("获取米家设备列表失败，请稍后重试") from exc

    async def inspect_device(
        self, query: str
    ) -> tuple[MijiaDeviceInfo, list[MijiaCapability], dict[str, str]]:
        async with self._lock:
            try:
                device = self._find_device(await self._ensure_devices(), query)
                capabilities = await asyncio.to_thread(self._load_capabilities, device)
                status = await asyncio.to_thread(self._load_status, device)
                return device, capabilities, status
            except MijiaClientError:
                raise
            except Exception as exc:
                logger.exception("[米家] 读取设备能力失败")
                raise MijiaClientError("读取米家设备能力失败，请稍后重试") from exc

    async def close(self) -> None:
        async with self._lock:
            if self._api is not None:
                await asyncio.to_thread(self._api.session.close)
                self._api = None
            if self._temp_dir is not None:
                self._temp_dir.cleanup()
                self._temp_dir = None

    async def _ensure_devices(self) -> list[MijiaDeviceInfo]:
        return await self._refresh_devices_locked(force=False)

    async def _ensure_devices_locked(self) -> list[MijiaDeviceInfo]:
        async with self._lock:
            return await self._ensure_devices()

    async def _refresh_devices_locked(self, *, force: bool) -> list[MijiaDeviceInfo]:
        if not force and self._devices is not None:
            return self._devices
        if self._devices_task is None:
            self._devices_task = asyncio.create_task(asyncio.to_thread(self._load_devices))
        task = self._devices_task
        try:
            devices = await asyncio.shield(task)
        finally:
            if task.done():
                self._devices_task = None
        self._devices = devices
        return devices

    async def execute(
        self, text: str
    ) -> tuple[MijiaDeviceInfo, str, str, str]:
        async with self._lock:
            try:
                device, operation = self._split_device(
                    await self._ensure_devices(), text
                )
                if not operation:
                    raise MijiaClientError("请发送：mi执行 设备名 操作")
                kind, name, value = await asyncio.to_thread(
                    self._execute_sync, device, operation
                )
                return device, kind, name, value
            except MijiaClientError:
                raise
            except (DeviceSetError, DeviceGetError) as exc:
                logger.warning(f"[米家] 设备操作被拒绝: {type(exc).__name__}")
                raise MijiaDeviceControlError("设备拒绝该操作，请检查名称和值") from exc
            except Exception as exc:
                logger.exception("[米家] 执行设备操作失败")
                raise MijiaClientError("执行米家设备操作失败，请稍后重试") from exc

    def _ensure_api(self) -> mijiaAPI:
        if self._api is None:
            self._temp_dir = tempfile.TemporaryDirectory(prefix="mijia-device-")
            auth_path = Path(self._temp_dir.name) / "auth.json"
            # _ensure_api 只在线程中调用，临时凭据写入不能回到事件循环。
            auth_path.write_text(self._auth_json, encoding="utf-8")
            self._api = mijiaAPI(str(auth_path))
            if not self._api.available:
                try:
                    self._api._refresh_token()
                except LoginError as exc:
                    raise MijiaAuthError("米家登录已失效，请重新登录") from exc
        return self._api

    @property
    def source_auth_json(self) -> str:
        return self._source_auth_json

    async def read_auth_json(self) -> str:
        if self._api is None:
            return self._auth_json
        self._auth_json = await asyncio.to_thread(
            self._api.auth_data_path.read_text, encoding="utf-8"
        )
        return self._auth_json

    def accept_auth_json(self, auth_json: str) -> None:
        self._auth_json = auth_json
        self._source_auth_json = auth_json

    def _load_devices(self) -> list[MijiaDeviceInfo]:
        api = self._ensure_api()
        homes = api.get_homes_list()
        owned = api.get_devices_list()
        shared = api.get_shared_devices_list()
        locations = self._locations(homes)
        rows: list[MijiaDeviceInfo] = []
        unique_rows: dict[str, dict[str, object]] = {}
        for row in owned:
            unique_rows[str(row["did"])] = row
        for row in shared:
            unique_rows.setdefault(str(row["did"]), row)
        for did, row in unique_rows.items():
            home_id = str(row.get("home_id", ""))
            home_name, room_id, room_name = locations.get(did, ("", "", ""))
            rows.append(
                MijiaDeviceInfo(
                    did=did,
                    name=str(row.get("name", "")),
                    model=str(row.get("model", "")),
                    spec_type=str(row.get("spec_type", "")),
                    home_id=home_id,
                    home_name=home_name,
                    room_id=room_id,
                    room_name=room_name,
                    is_online=self._bool_or_none(row.get("isOnline")),
                )
            )
        return rows

    @staticmethod
    def _locations(homes: list[dict[str, object]]) -> dict[str, tuple[str, str, str]]:
        result: dict[str, tuple[str, str, str]] = {}
        for home in homes:
            rooms = home.get("roomlist")
            if not isinstance(rooms, list):
                continue
            for room in rooms:
                if not isinstance(room, dict):
                    continue
                dids = room.get("dids")
                if not isinstance(dids, list):
                    continue
                for did in dids:
                    result[str(did)] = (
                        str(home.get("name", "")),
                        str(room.get("id", "")),
                        str(room.get("name", "")),
                    )
        return result

    @staticmethod
    def _bool_or_none(value: object) -> bool | None:
        if isinstance(value, bool):
            return value
        return None

    @staticmethod
    def _normalize_name(name: str) -> str:
        return "".join(name.split())

    def _find_device(self, devices: list[MijiaDeviceInfo], query: str) -> MijiaDeviceInfo:
        target = self._normalize_name(query)
        matches = [device for device in devices if self._normalize_name(device["name"]) == target]
        if not matches:
            raise MijiaDeviceNotFoundError(f"未找到名为“{query}”的设备")
        if len(matches) > 1:
            raise MijiaDeviceAmbiguousError(f"设备“{query}”匹配到多个设备，请修改米家设备名称")
        return matches[0]

    def _split_device(
        self, devices: list[MijiaDeviceInfo], text: str
    ) -> tuple[MijiaDeviceInfo, str]:
        candidates: list[tuple[int, MijiaDeviceInfo, int]] = []
        normalized_text = self._normalize_name(text)
        for device in devices:
            normalized_name = self._normalize_name(device["name"])
            if not normalized_text.startswith(normalized_name):
                continue
            offset = self._consumed_offset(text, normalized_name)
            if offset is None:
                continue
            candidates.append((len(normalized_name), device, offset))
        if not candidates:
            raise MijiaDeviceNotFoundError(f"未找到设备：{text}")
        candidates.sort(key=lambda item: item[0], reverse=True)
        longest = candidates[0][0]
        matches = [item for item in candidates if item[0] == longest]
        if len(matches) > 1:
            names = "、".join(item[1]["name"] for item in matches)
            raise MijiaDeviceAmbiguousError(f"匹配到多个设备：{names}")
        _, device, offset = matches[0]
        return device, text[offset:].lstrip()

    @staticmethod
    def _consumed_offset(text: str, normalized_name: str) -> int | None:
        target = normalized_name
        index = 0
        matched = 0
        while index < len(text) and matched < len(target):
            char = text[index]
            index += 1
            if char.isspace():
                continue
            if char != target[matched]:
                return None
            matched += 1
        return index if matched == len(target) else None

    def _load_capabilities(self, device_info: MijiaDeviceInfo) -> list[MijiaCapability]:
        spec = self._load_spec(device_info)
        capabilities: list[MijiaCapability] = []
        properties = spec.get("properties")
        if isinstance(properties, list):
            for prop in properties:
                if not isinstance(prop, dict):
                    continue
                rw = str(prop.get("rw", ""))
                values: list[str] = []
                value_list = prop.get("value-list")
                if isinstance(value_list, list):
                    for item in value_list:
                        if not isinstance(item, dict):
                            continue
                        label = str(item.get("desc_zh_cn") or item.get("description") or "")
                        if label:
                            values.append(f"{item.get('value')}={label}")
                capabilities.append(
                    MijiaCapability(
                        name=str(prop.get("name", "")),
                        description=str(prop.get("description", "")),
                        kind="property",
                        readable="r" in rw,
                        writable="w" in rw,
                        values=values,
                    )
                )
        actions = spec.get("actions")
        if isinstance(actions, list):
            for action in actions:
                if not isinstance(action, dict):
                    continue
                capabilities.append(
                    MijiaCapability(
                        name=str(action.get("name", "")),
                        description=str(action.get("description", "")),
                        kind="action",
                        readable=False,
                        writable=False,
                        values=[],
                    )
                )
        return capabilities

    def _load_status(self, device_info: MijiaDeviceInfo) -> dict[str, str]:
        spec = self._load_spec(device_info)
        api = self._ensure_api()
        properties = spec.get("properties")
        if not isinstance(properties, list):
            return {}
        requests: list[dict[str, object]] = []
        names: list[str] = []
        for prop in properties:
            if not isinstance(prop, dict):
                continue
            if "r" not in str(prop.get("rw", "")):
                continue
            method = prop.get("method")
            if not isinstance(method, dict):
                continue
            item = dict(method)
            item["did"] = device_info["did"]
            requests.append(item)
            names.append(str(prop.get("name", "")))
        if not requests:
            return {}
        results = api.get_devices_prop(requests)
        if not isinstance(results, list):
            return {}
        status: dict[str, str] = {}
        for name, result in zip(names, results):
            if not isinstance(result, dict) or result.get("code") != 0:
                continue
            status[name] = str(result.get("value", ""))
        return status

    def _load_spec(self, device_info: MijiaDeviceInfo) -> dict[str, object]:
        spec_type = device_info["spec_type"]
        if not spec_type:
            raise MijiaClientError("米家未返回该设备的 spec_type，暂无法读取或控制")
        spec = self._specs.get(spec_type)
        if spec is None:
            spec = get_device_info(spec_type)
            self._specs[spec_type] = spec
        return spec

    def _execute_sync(
        self, device_info: MijiaDeviceInfo, operation: str
    ) -> tuple[str, str, str]:
        spec = self._load_spec(device_info)
        properties = spec.get("properties")
        actions = spec.get("actions")
        prop_items = properties if isinstance(properties, list) else []
        action_items = actions if isinstance(actions, list) else []
        tokens = operation.split(None, 1)

        if len(tokens) == 2:
            prop_name, value = tokens
            if self._match_capability(prop_items, prop_name) is None:
                raise MijiaDeviceControlError(f"设备不支持属性“{prop_name}”")
            self._set_property(device_info, prop_name, value)
            return "property", prop_name, value

        operation = tokens[0]
        if operation in ("开", "关"):
            prop = self._match_capability(prop_items, "on")
            if prop is None:
                raise MijiaDeviceControlError("该设备没有可写的 on 属性")
            self._set_property(device_info, "on", operation)
            return "power", "on", operation

        if self._match_capability(action_items, operation) is not None:
            self._run_action(device_info, operation)
            return "action", operation, ""

        if self._match_capability(prop_items, operation) is not None:
            raise MijiaDeviceControlError("设置属性时需要提供值，例如：mi执行 台灯 亮度 60")
        raise MijiaDeviceControlError(f"设备不支持操作“{operation}”")

    def _set_property(self, device_info: MijiaDeviceInfo, prop_name: str, raw_value: str) -> None:
        spec = self._load_spec(device_info)
        properties = spec.get("properties")
        if not isinstance(properties, list):
            raise MijiaClientError("设备规格没有属性列表")
        target = self._match_capability(properties, prop_name)
        if target is None:
            raise MijiaDeviceControlError(f"设备不支持属性“{prop_name}”")
        if "w" not in str(target.get("rw", "")):
            raise MijiaDeviceControlError(f"属性“{prop_name}”不可写")
        prop = DevProp(target)
        method = dict(prop.method)
        method["did"] = device_info["did"]
        method["value"] = self._coerce_value(prop, raw_value)
        api = self._ensure_api()
        result = api.set_devices_prop(method)
        if result.get("code") not in (0, 1):
            raise MijiaDeviceControlError(str(result.get("message", "设备拒绝设置属性")))

    def _run_action(self, device_info: MijiaDeviceInfo, action_name: str) -> None:
        spec = self._load_spec(device_info)
        actions = spec.get("actions")
        if not isinstance(actions, list):
            raise MijiaClientError("设备规格没有动作列表")
        target = self._match_capability(actions, action_name)
        if target is None:
            raise MijiaDeviceControlError(f"设备不支持动作“{action_name}”")
        action = DevAction(target)
        method = dict(action.method)
        method["did"] = device_info["did"]
        api = self._ensure_api()
        result = api.run_action(method)
        if result.get("code") not in (0, 1):
            raise MijiaDeviceControlError(str(result.get("message", "设备拒绝执行动作")))

    @staticmethod
    def _match_capability(items: list[object], name: str) -> dict[str, object] | None:
        normalized = name.strip().lower().replace("_", "-")
        for item in items:
            if not isinstance(item, dict):
                continue
            item_name = str(item.get("name", ""))
            if item_name.strip().lower().replace("_", "-") == normalized:
                return item
        return None

    @staticmethod
    def _coerce_value(prop: DevProp, raw_value: str) -> bool | int | float | str:
        normalized = raw_value.strip().lower()
        value_list = prop.__dict__.get("value_list")
        if isinstance(value_list, list):
            for item in value_list:
                if not isinstance(item, dict):
                    continue
                labels = (
                    str(item.get("desc_zh_cn") or ""),
                    str(item.get("description") or "").split(" / ", 1)[0],
                )
                if any(label.strip().lower() == normalized for label in labels if label):
                    return item["value"]
        if prop.type == "bool":
            if normalized in ("true", "1", "on", "开"):
                return True
            if normalized in ("false", "0", "off", "关"):
                return False
            raise MijiaDeviceControlError("该属性需要布尔值，请使用 true/false 或 开/关")
        if prop.type in ("int", "uint"):
            try:
                return int(raw_value)
            except ValueError as exc:
                raise MijiaDeviceControlError("该属性需要整数") from exc
        if prop.type == "float":
            try:
                return float(raw_value)
            except ValueError as exc:
                raise MijiaDeviceControlError("该属性需要数字") from exc
        return raw_value


class MijiaClientRegistry:
    """按机器人用户与米家账号复用客户端；凭据变化时由调用方关闭旧会话。"""

    _sessions: dict[tuple[str, str], MijiaDeviceSession]

    def __init__(self) -> None:
        self._sessions = {}

    async def get(
        self, user_id: str, mijia_user_id: str, auth_json: str
    ) -> MijiaDeviceSession:
        key = (user_id, mijia_user_id)
        session = self._sessions.get(key)
        if session is not None and session.source_auth_json != auth_json:
            await session.close()
            session = None
        if session is None:
            session = MijiaDeviceSession(auth_json)
            self._sessions[key] = session
        return session


MIJIA_CLIENTS = MijiaClientRegistry()
