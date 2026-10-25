# MIUID 开发约定

本文件适用于 `MIUID` 插件的全部代码、命令、渲染与数据处理。
与用户当轮指令冲突时以用户指令为准；规范未覆盖或存在多种实现方式时先询问。

## 插件结构

结构参考 SteamUID，按职责分层；新增业务使用 `miuid_<feature>` 命令包。

```text
MIUID/
├── __init__.py
├── __nest__.py
├── AGENTS.md
├── ICON.png
├── pyproject.toml
├── README.md
├── docs/
│   ├── output/                 # 预览图、排版测试与临时产物
│   └── ...                     # 参考资料，不参与插件运行
├── test/                       # 验证脚本，不随插件发布
└── MIUID/
    ├── __init__.py             # 插件注册入口
    ├── __full__.py
    ├── version.py
    ├── miuid_<feature>/        # 一个目录负责一个命令域
    │   ├── __init__.py         # SV 与触发器注册，只放简单入口逻辑
    │   └── <feature>_services.py
    ├── miuid_config/
    ├── miuid_help/
    └── utils/
        ├── database/           # 数据表与数据访问，一张表一个文件
        ├── utils/              # 与业务无关的通用函数
        ├── api/                # 第三方接口交互
        ├── downloader.py       # 统一下载入口
        ├── helper/             # 依赖业务语义的通用逻辑
        └── render/             # 图片渲染
```

- 命令包目录名统一为小写下划线形式，不新建驼峰目录。
- 复杂实现放入 `*_services.py`，`__init__.py` 只做注册与简单转发。
- 临时产物统一放在 `docs/output/`，不得散落到工作区其他位置。
- 不顺手重构无关代码，不扩大改动面。

## SQLModel

SQLModel 禁止定义 `__tablename__`。表名由类名自动推导：全小写、无下划线。

```python
# 正确：MihomeDevice -> mihomedevice
class MihomeDevice(SQLModel, table=True):
    device_id: str = Field(primary_key=True)


# 错误：禁止手动指定表名
class MihomeDevice(SQLModel, table=True):
    __tablename__ = "mihome_devices"
```

新增表沿用 SteamUID 的组织方式，一张表及其数据访问逻辑放在同一个文件中。

## 异步要求

这是一个完全异步的项目。所有可能阻塞的方法，包括网络、文件、数据库、渲染等，
都必须定义为 `async def` 并通过 `await` 调用。

- 不使用 `time.sleep`，改用 `asyncio.sleep`。
- 不在事件循环中直接执行同步网络或文件 I/O。
- 新增函数必须保持异步调用链完整，不能用同步包装函数绕过。

## 注释

`#` 注释最多连续两行，每行不超过 88 个字符。

- 代码能够自解释时不写注释，禁止把 Python 翻译成中文。
- 只写为什么这样做、有什么坑或边界条件，不写代码做了什么。
- 两行讲不清说明逻辑应拆分函数或改进命名，而不是继续堆注释。

```python
# 群聊 user_id 置空以保证同群共享同一个 deque
async def handle(msg: Message) -> None:
    ...
```

## 模块引用与依赖

- 使用工具时直接 import 到具体文件：
  `from ..utils.downloader import download`。
- 禁止在 `__init__.py` 使用 `__all__` 聚合转发函数；调用方必须指向真实模块。
- 确需在包入口提前初始化时，必须先征得用户确认再修改。
- 只允许上层依赖下层，禁止环状 import。

依赖方向自下而上：

```text
utils/database、utils/utils、utils/api、utils/downloader
        ↓
utils/helper
        ↓
utils/render
        ↓
miuid_*/xxx_services.py
        ↓
miuid_*/__init__.py
```

- `utils/**` 不得 import 任何命令包。
- `utils/api/` 只做接口交互，不得依赖 `utils/helper/` 或 `utils/render/`。
- `utils/render/` 不得 import 命令包或 `*_services.py`。
- 命令包之间不得互相引用内部实现。

## 命令设计

触发器按下表选择：

| 命令形态 | 触发器 | 说明 |
| --- | --- | --- |
| 无参数 | `on_fullmatch` | 整条消息完整匹配 |
| 参数固定跟在命令后 | `on_prefix` | 命令作前缀，后文为参数区 |
| 参数可有可无 | `on_command` | 命令词匹配，后文可空 |

空格分隔型参数按 `ev.text` 的空格切分，按下标顺序取值。实参不足时对应位置
视为空字符串，不做缺省补全或容错猜测。

句中占位型参数使用正则捕获组直接提取，不得改用空格切分。

注册命令时遵守以下规则：

- 只注册明确要求的关键词，禁止私加别名、近义词或大小写变体。
- 多个明确要求的别名用元组一次注册，不写多个装饰器：

```python
@sv.on_prefix(("登录", "login"), block=True)
async def _(bot: Bot, ev: Event) -> None: ...
```

- 命令默认 `block=True`，避免串触发。
- 与既有命令冲突时先询问，不得擅自调整优先级或删改旧命令。
- 新增命令后必须检查是否会被其他触发器抢先匹配。

## 实现范围与兼容

- 用户指定方案 A 时只实现 A，不擅自扩展或并行实现 B。
- 指令参数、选项、平台代码和枚举值严格按用户指定的代码判断。
- 禁止为参数私加中文名、英文名、拼音缩写等别名字典或兼容映射。
- 禁止把抓包记录、测试样本或本地数据作为生产默认值或兜底数据。
- 不维护旧代码兼容层；新实现与旧实现冲突时直接修改旧代码。
- 只有会破坏历史用户数据或既有指令行为时，才交由用户决定是否兼容。
- 不写别名表，不做旧路径 re-export，不维护废弃前缀列表。
- 函数升级直接修改函数本体；与现有业务逻辑冲突时先询问。
- 不为 gsuid_core 版本差异或插件结构变化写条件分支，数据库兼容除外。
- 不把业务堆回巨型上帝文件，不使用挂载式兼容包装。

## 渲染与数据

- 图片渲染优先使用框架自带的 `pytakumi`。
- `pytakumi` 无法完成时先询问用户解决方案，不得擅自修改未提及的视觉效果。
- 渲染预览、排版测试和临时数据统一放在 `docs/output/`。
- 第三方 JSON 接口随用随请求，不写入硬盘。
- 除非用户明确要求保存到本地，否则接口数据不得落盘。

## 错误处理与日志

面向用户时，先明确告知运行出错，再给出简要原因或下一步建议。

- 不向用户抛出堆栈，不暴露内部路径、令牌或原始响应体。
- 详细异常和必要的敏感上下文只写入 `logger`。
- 生产路径禁止使用 `print`，不得把调试输出残留给用户。
- 所有日志统一使用前缀 `[米家] `。

```python
logger.info("[米家] 开始查询设备状态")
logger.exception("[米家] 设备状态查询失败")
```

## 提交前自检

- 未使用 `__tablename__`，表名符合类名推导规则。
- 所有阻塞路径均为 `async def`，调用链已正确 `await`。
- 注释不超过两行，每行不超过 88 个字符，且只说明原因或坑。
- import 直达真实模块，无 `__all__` 聚合转发，无环状依赖。
- 未添加未要求的命令、别名、参数、枚举映射或兼容分支。
- 用户错误提示无堆栈、路径、令牌与原始响应体，日志带 `[米家] ` 前缀。
- 渲染优先使用 `pytakumi`，临时产物仅位于 `docs/output/`。
- 未将第三方 JSON 或测试样本写入生产数据，未扩大无关改动面。
