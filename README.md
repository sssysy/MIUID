# MIUID

<p align="center">
  <a href="ICON.png">
    <img src="ICON.png" width="227" height="227" alt="MIUID">
  </a>
</p>
<h1 align="center">MIUID 0.1.0</h1>
<h4 align="center">基于 gsuid_core 的米家账号插件</h4>

<p align="center">
  <a href="https://www.python.org/" target="_blank"><img src="https://img.shields.io/badge/Python-3.12+-blue" alt="Python 3.12+"></a>
  <a href="https://github.com/Genshin-bots/gsuid_core" target="_blank"><img src="https://img.shields.io/badge/gsuid_core-0.11.1+-orange" alt="gsuid_core 0.11.1+"></a>
</p>

<div align="center">
  <a href="https://docs.sayu-bot.com/" target="_blank">安装文档</a> &nbsp; · &nbsp;
  <a href="https://github.com/Genshin-bots/gsuid_core" target="_blank">gsuid_core</a>
</div>

## 丨安装提醒

> **注意：该插件为 [早柚核心(gsuid_core)](https://github.com/Genshin-bots/gsuid_core) 的扩展，具体安装方式可参考上方安装文档**
>
> 🚧 项目处于早期开发阶段，有问题可提 issue 或 pr 🚧

## 丨命令列表

<details><summary>账号管理</summary>

| 命令 | 说明 |
|------|:------:|
| `mi登录` | 扫码登录米家账号，并将登录账号设为当前默认账号 |
| `mi登出` | 登出并删除当前默认米家账号，其他已保存账号不受影响 |
| `mi查看` | 查看当前用户已登录的米家账号与默认账号标记 |

</details>

<details><summary>设备管理</summary>

| 命令 | 说明 |
|------|:------:|
| `mi设备列表` | 列出当前米家账号所有家庭的全部设备 |
| `mi查看 设备名` | 查看设备能力与实时状态 |
| `mi执行 设备名 开` / `mi执行 设备名 关` | 开启或关闭设备 |
| `mi执行 设备名 属性 值` | 设置设备属性，例如亮度、温度或模式 |
| `mi执行 设备名 动作` | 执行设备动作 |

</details>

<details><summary>其他</summary>

| 命令 | 说明 |
|------|:------:|
| `mi帮助` | 获取 MIUID 帮助图 |

</details>

## 丨其他

- 本项目仅供学习使用，请勿用于商业用途
- 请遵守小米账号与米家服务的使用条款

## 致谢

- [Wuyi 无疑](https://github.com/KimigaiiWuyi)
- [gsuid_core](https://github.com/Genshin-bots/gsuid_core)
- [mijiaAPI](https://github.com/Do1e/mijia-api)
