from gsuid_core.utils.plugins_config.models import (
    GSC,
    GsBoolConfig,
    GsIntConfig,
)

CONFIG_DEFAULT: dict[str, GSC] = {
    "cache_ttl_minutes": GsIntConfig(
        title="缓存时长（分钟）",
        desc="查询结果的本地缓存时长；0 表示不缓存",
        data=30,
    ),
    "enable_debug": GsBoolConfig(
        title="调试日志",
        desc="开启后输出 MIUID 的调试日志",
        data=False,
    ),
}
