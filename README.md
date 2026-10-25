# MIUID

MIUID 是面向 GsCore 的插件基础框架。当前版本提供可运行的加载入口、配置、帮助、状态卡和示例命令，业务模块按同一模式继续添加。

## 目录

```text
MIUID/
├── __init__.py
├── __nest__.py
├── pyproject.toml
├── ruff.toml
├── pyrightconfig.json
├── ICON.png
└── MIUID/
    ├── __init__.py
    ├── __full__.py
    ├── version.py
    ├── miuid_config/
    │   ├── __init__.py
    │   ├── config_default.py
    │   └── miuid_config.py
    ├── miuid_help/
    │   ├── __init__.py
    │   ├── get_help.py
    │   └── help.json
    ├── miuid_status/
    │   └── __init__.py
    ├── miuid_template/
    │   └── __init__.py
    └── utils/
        └── resource/
            ├── __init__.py
            └── RESOURCE_PATH.py
```

## 命令

默认前缀为 `miuid`。示例：

```text
miuid ping
miuid 帮助
```

以后添加业务模块时，在 `MIUID/MIUID/` 下新建 `miuid_<feature>/`，让模块在导入时注册 `SV` 与触发器即可。

## 配置与数据

运行时文件写入 `data/MIUID/`：

- `data/MIUID/config.json`：插件配置
- `data/MIUID/cache/`：缓存
- `data/MIUID/resource/`：下载或用户上传的资源

## 验证

在 Core 仓库根目录执行：

```powershell
uv run ruff check gsuid_core/plugins/MIUID
uv run ruff format --check gsuid_core/plugins/MIUID
uv run basedpyright gsuid_core/plugins/MIUID
```
