# Codex Quota Guard

[English README](../README.md) · [架构](architecture.md) · [估算算法](estimation.md) · [隐私与安全](privacy-and-security.md)

Codex Quota Guard 是一个 Windows 本地系统托盘工具。它把 Codex 官方返回的 5 小时/周使用百分比，与可获得的累计 token 数据按重置周期对齐，逐步估算当前周期的绝对总量、已用量和剩余量。

最重要的约束是：**查看额度本身不产生任何模型推理调用。**

![使用示例数据渲染的界面](assets/dashboard-overview.png)

> 截图使用虚构示例数据。正常运行时程序不会注入演示数值。本项目不是 OpenAI 官方产品，也不能增加、重置、绕过或修改 Codex 限额。

## 已实现功能

- Qt 6/QML 深色桌面界面，支持普通窗口、最大化和窄窗口自适应。
- Windows 原生托盘：关闭窗口后继续监测，可从托盘打开、刷新或退出。
- 托盘图标优先显示 Weekly 剩余百分比的整数，不带 `%`；低于 10 时补零，Weekly 缺失时回退到 5 小时窗口。
- 鼠标悬停托盘图标可查看 5h/Weekly 的剩余、已用、重置时间和最后更新时间；托盘菜单还会显示绝对估算、置信度与数据源状态。
- 分别维护 5 小时与 Weekly calibration epoch，绝不混合拟合。
- 使用 Theil–Sen 鲁棒斜率估计 `Q = 100b`，支持周期中途安装。
- 有效使用跨度不足约 5 个百分点时只显示“正在校准”。
- 基于样本数、跨度、残差、局部斜率一致性、完整性、时效、延迟和模型差异计算 0–100 置信度。
- 保存完整历史周期，形成中位数/MAD baseline，并在高置信度显著偏离时提示可能的额度变化。
- SQLite 本地存储、日志自动脱敏、single-flight、缓存、退避、jitter 和断网恢复。
- 34 项自动化测试，测试本身不访问模型。

## 零推理边界

出站 RPC 请求白名单只有：

```text
initialize
account/rateLimits/read
account/usage/read
```

唯一允许的出站通知是 `initialized`；程序可接收 `account/rateLimits/updated` 作为刷新信号。

以下操作会在进入传输层之前直接拒绝：

- `turn/start`
- `thread/start`
- Responses / Chat Completions
- reset credit 消费
- 账户写入
- 任何未知 RPC 方法

程序通过本机 `codex app-server` 复用已有登录状态，不读取、保存或上传 access token、refresh token、Cookie 或 Authorization header。

## 快速开始

### 使用发布包

从 [Releases](https://github.com/lhfhybxm/codex-quota-guard/releases) 下载 Windows 压缩包并完整解压，然后运行 `CodexQuotaGuard.exe`。不要只单独移动 EXE，因为 Qt 运行库位于同目录的 `_internal` 中。

### 从源码运行

需要 Windows 10/11、Python.org CPython 3.11 和已登录的 Codex CLI。

```powershell
git clone https://github.com/lhfhybxm/codex-quota-guard.git
cd codex-quota-guard
.\scripts\Setup.ps1
.\scripts\Start-CodexQuotaGuard.ps1
```

安装脚本只创建项目内的 `.venv-win`，不会全局安装依赖。`Start-CodexQuotaGuard.ps1` 默认直接进入托盘；使用 `-NoTray` 可在排错时保留前台窗口。

执行一次脱敏只读探测：

```powershell
.\.venv-win\Scripts\python.exe -m codex_quota_guard --once
```

构建 Windows 发布目录：

```powershell
.\scripts\Build.ps1
```

每次构建都会创建新的 `publish\时间戳\` 目录，不覆盖旧版本。

## 托盘数字含义

托盘图标中的数字表示**官方窗口的剩余百分比**，不是已用百分比，也不是估算 credits：

- 默认显示 Weekly 剩余百分比并四舍五入为整数，例如 `75`；
- 低于 10 时显示为两位，例如 `04`；
- 完全未使用时为避免误导，诚实显示 `100`；
- Weekly 未返回时自动显示 5 小时窗口；
- 两个窗口都不可用时显示 `--`，不会制造一个假数字。

悬停信息保留一位小数，并同时显示已用比例、重置时间与最近成功更新时间。

## 当前数据含义

当前 Codex App Server 可以返回官方百分比、重置时间、窗口时长和 lifetime token/daily token buckets，但没有返回可用于精确换算的模型拆分、input/cached/output token、estimated credits 或美元 cost。因此：

- 百分比标为官方数据；
- 当前绝对估算只能标为 `tokens`；
- credits、API 等价美元和 Plus 订阅价格不会相互替代；
- 无法获得的字段保留为 `null`，不会伪造为 0；
- 私有 `wham/usage` 目前没有作为活动 Provider 启用。

## 本地数据

```text
%LOCALAPPDATA%\CodexQuotaGuard\quota.db
%LOCALAPPDATA%\CodexQuotaGuard\app.log
```

程序不会把本地额度历史上传到云端。真实只读验证的脱敏摘要见 [real-read-2026-08-20.md](real-read-2026-08-20.md)。

如果界面出现完整旧文案 `UNAVAILABLE · Source: Codex App Server · Last updated: never`，说明运行的是未发布的 Qt 迁移前测试包。请先从托盘退出旧进程，把最新 Release 解压到一个全新目录，再运行其中的 EXE；不要把新旧 `publish\...` 目录混合覆盖。

## 开源说明

项目采用 [MIT License 英文原文](../LICENSE)，并提供[中文参考译文](../LICENSE.zh-CN.md)。如有差异，以英文原文为准。OpenAI 与 Codex 商标归其权利人所有，本项目仅作描述性使用。
