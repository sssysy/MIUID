"""米家设备属性、枚举值与单位的中文展示映射。"""

import re

PROPERTY_NAMES: dict[str, str] = {
    "ac-ctrl-library": "空调控制库",
    "ac-ctrl-library-crc32": "空调控制库校验值",
    "ac-state": "空调状态",
    "ac-type": "空调类型",
    "ac-work-mode": "空调工作模式",
    "air-quality": "空气质量",
    "alarm": "提示音",
    "anti-flicker": "防闪烁模式",
    "battery": "电池状态",
    "battery-level": "电池电量",
    "blood-oxygen": "血氧",
    "brand-id": "品牌信息",
    "brightness": "亮度",
    "calories": "热量",
    "charging-state": "充电状态",
    "color": "颜色",
    "color-temperature": "色温",
    "connected-device-number": "连接设备数",
    "current": "电流",
    "current-keep-warm": "当前保温状态",
    "current-position": "当前位置",
    "detection-distance": "探测距离",
    "distance": "距离",
    "download-speed": "下载速率",
    "electric-power": "功率",
    "fan-level": "风速",
    "fault": "故障",
    "filter-left-time": "滤芯剩余时间",
    "filter-life-level": "滤芯剩余寿命",
    "filter-used-time": "滤芯已使用时间",
    "heat-level": "火力",
    "heart-rate": "心率",
    "horizontal-swing": "左右扫风",
    "illumination": "光照度",
    "indicator-light": "指示灯",
    "keepwarm-set": "保温设置",
    "left-time": "剩余时间",
    "light-intensity": "光照强度",
    "match-state": "匹配状态",
    "mode": "模式",
    "motion-state": "人体移动状态",
    "mute": "静音",
    "no-motion-duration": "无人移动时长",
    "on": "开关",
    "play-control": "播放控制",
    "play-state": "播放状态",
    "physical-controls-locked": "童锁",
    "pm2.5-density": "PM2.5 浓度",
    "position": "位置",
    "power": "功率",
    "power-consumption": "用电量",
    "power-on-state": "上电状态",
    "presence-state": "存在状态",
    "recipe-name": "食谱",
    "relative-humidity": "湿度",
    "remote-id": "遥控器 ID",
    "signal-strength": "信号强度",
    "sleep-state": "睡眠状态",
    "set-ac-ctrl-info": "设置空调控制信息",
    "set-ac-model": "设置空调型号",
    "ssid": "Wi-Fi 名称",
    "status": "状态",
    "steps": "步数",
    "target-temperature": "目标温度",
    "target-position": "目标位置",
    "target-time": "目标时间",
    "temperature": "温度",
    "texture": "口感",
    "toggle": "切换开关状态",
    "upload-speed": "上传速率",
    "volume": "音量",
    "wake-up-mode": "唤醒模式",
    "wearing-state": "佩戴状态",
    "vertical-swing": "上下扫风",
    "vol": "内部电压",
    "voltage": "电压",
    "wiring-method": "接线方式",
}

VALUE_LABELS: dict[str, str] = {
    "ac mode with outlet": "空调插在插座上",
    "ac mode without outlet": "空调没插在插座上",
    "auto": "自动",
    "abnormal": "异常",
    "charging": "充电中",
    "close": "关",
    "closed": "关",
    "closing": "正在关闭",
    "connected": "已连接",
    "cool": "制冷",
    "detected": "已检测到",
    "disconnected": "未连接",
    "dry": "除湿",
    "error": "异常",
    "fan": "送风",
    "false": "关",
    "full": "已充满",
    "heat": "制热",
    "high": "高",
    "idle": "空闲",
    "low": "低",
    "manual": "手动",
    "matching": "匹配中",
    "medium": "中",
    "medium-high": "中高",
    "medium-low": "中低",
    "motion": "有人移动",
    "neutral wire": "有零线",
    "no": "否",
    "no fault": "无故障",
    "no motion": "无人移动",
    "no neutral": "无零线",
    "normal": "正常",
    "not charging": "未充电",
    "not detected": "未检测到",
    "not wearing": "未佩戴",
    "occupied": "有人",
    "off": "关",
    "offline": "离线",
    "on": "开",
    "online": "在线",
    "open": "开",
    "opened": "开",
    "opening": "正在打开",
    "out of matching": "未匹配中",
    "overheat": "过热",
    "overload": "过载",
    "paused": "已暂停",
    "playing": "播放中",
    "quiet": "静音",
    "silent": "静音",
    "stateful": "有状态空调",
    "stateless": "无状态空调",
    "stopped": "已停止",
    "strong": "强",
    "true": "开",
    "turbo": "强力",
    "unknown": "未知",
    "unoccupied": "无人",
    "wearing": "已佩戴",
    "yes": "是",
}

PROPERTY_UNITS: dict[str, str] = {
    "battery-level": "%",
    "current": " A",
    "electric-power": " W",
    "pm2.5-density": " μg/m³",
    "power": " W",
    "relative-humidity": "%",
    "target-temperature": " °C",
    "temperature": " °C",
    "voltage": " V",
}

# 这些属性只用于内部通信或能力匹配，展示给用户没有意义。
HIDDEN_PROPERTIES: set[str] = {
    "ac-ctrl-library",
    "ac-ctrl-library-crc32",
    "ac-type",
    "brand-id",
    "remote-id",
}

_CHANNEL_PATTERN = re.compile(r"^(?P<base>.+)-(?P<channel>\d+)$")
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")


def normalize_key(name: str) -> str:
    return name.strip().lower().replace("_", "-").replace(" ", "-")


def split_property_name(name: str) -> tuple[str, int | None]:
    normalized = normalize_key(name)
    matched = _CHANNEL_PATTERN.fullmatch(normalized)
    if matched:
        return matched.group("base"), int(matched.group("channel"))
    return normalized, None


def display_property_name(name: str, description: str = "") -> str:
    base, channel = split_property_name(name)
    label = PROPERTY_NAMES.get(base)
    if label:
        return f"{label} {channel}" if channel is not None else label
    return _preferred_description(description) or name


def display_value_option(value: object, label: str) -> str:
    return f"{value}={translate_value_label(label)}"


def translate_value_label(label: str) -> str:
    text = label.strip().rstrip("。")
    if not text or _CJK_PATTERN.search(text):
        return text
    return VALUE_LABELS.get(normalize_key(text).replace("-", " "), text)


def format_status_value(
    property_name: str,
    raw_value: object,
    value_type: str,
    options: list[tuple[str, str]],
) -> str:
    raw = str(raw_value)
    for option_value, option_label in options:
        if option_value == raw:
            return translate_value_label(option_label)

    normalized = raw.strip().lower()
    if value_type == "bool":
        return "开" if normalized in ("1", "true") else "关"

    value = translate_value_label(raw)
    unit = PROPERTY_UNITS.get(split_property_name(property_name)[0], "")
    if unit and _is_number(value):
        return f"{value}{unit}"
    return value


def _preferred_description(description: str) -> str:
    parts = [part.strip() for part in description.split(" / ") if part.strip()]
    for part in reversed(parts):
        if _CJK_PATTERN.search(part):
            return part
    return " / ".join(parts)


def _is_number(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True
