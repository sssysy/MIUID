"""MIUID plugin entry."""

from gsuid_core.sv import Plugins

# 在框架 create_all 前注册插件数据表。
from .utils import database  # noqa: F401

Plugins(
    name="MIUID",
    force_prefix=["miuid"],
    allow_empty_prefix=False,
)
