# 墨析 OCR · DeepSeek 接手入口

交接日期：2026-10-23。此包是**源码与工单，不是安装包**。只交接项目，不授权接手方立即安装、发布、下载模型或操作用户扫描数据。

## 先看这三个事实

| 对象 | 已核对的来源 | 当前含义 |
| --- | --- | --- |
| 交接前最新功能源码 | `352665be7f147474af1cf93f522958e3972cb052`，PR #11 已合并 | 包含 MLX 闲置缓存优化；本次交接 PR 只补文档 |
| 公开候选安装包 | `v1.3.0-rc.2`，源 `3e9a7e2ea2bc33fd58cafd33520a1928599a28c3` | 含阅读配色修复，**不含 MLX 优化**；非正式版 |
| 用户当前 Mac 安装版 | 1.3.0 (build 6)，源 `b7d29292c18aa30fa00e4aef9f33ca57663100ad` | 含阅读配色修复，**不含 MLX 优化**；本次不替换 |

最终交接 ZIP 从文档 PR 合并后的干净 main 导出；准确打包提交在 ZIP 的 Git archive 注释中，并在随包校验/交付记录中列出。上述功能基线不冒充交接文档的最终提交。状态会随项目推进变化，接手时重新核对远端和目标机器。

## 阅读顺序

1. [AGENTS.md](AGENTS.md) 和 [MAINTENANCE_RULES.md](MAINTENANCE_RULES.md)：必须完整阅读，复述六步后才可修改。
2. [详细交接说明](handoff/DEEPSEEK_HANDOFF.md)：架构、版本、环境、数据边界、命令、证据和故障定位。
3. [接手工单](handoff/WORK_ORDERS.md)：先完成 DS-00 基线检查，再由用户确认下一张工单。
4. 按平台读 [DEPLOYMENT.md](DEPLOYMENT.md)、[MLX_PERFORMANCE.md](MLX_PERFORMANCE.md) 或 [WINDOWS_CODEX_HANDOFF.md](WINDOWS_CODEX_HANDOFF.md)。历史 Windows 文档中的旧版本文件名以本交接说明及当前源码为准。

## 可以直接交给 DeepSeek 的首条指令

> 你将接手“墨析 OCR 工作台”，唯一仓库是 https://github.com/cpcboy/ximo-ocr 。请先完整读 AGENTS.md、MAINTENANCE_RULES.md、START_HERE-DEEPSEEK.md、handoff/DEEPSEEK_HANDOFF.md、handoff/WORK_ORDERS.md，再复述“最小改动 → 独立对抗 review → 文档 → PR/CI/合并 → 经授权备份部署 → 真实用户路径验证”及本次风险。首先只执行 DS-00 的只读基线核对；报告当前机器、源码/安装版/公开候选差异、已有证据与未验范围，以及建议下一张工单，等我确认后再实施。不要把历史单次安装/退出/发布授权延续到新机器或新版本。不要读取/上传扫描原件、结果、阅读笔记或凭据；不要加载/下载模型、启动生产后端、改生产安装目录、关闭安全软件或扩大本机 API 权限。所有修改走主题分支、独立 review、PR、成功 CI、合并；不能直接推 main。ZIP 无 .git，正式开发必须重新 clone 官方仓库；不能伪造 SOURCE_COMMIT 或绕过构建门禁。MLX 优化已在源码合并，但尚未进入公开安装包或本机安装版；不要重复实现或宣称已部署。缺少执行环境、授权或独立 reviewer 时如实报告，不能把未执行步骤登记完成。

## 包里有什么 / 没有什么

- 包含完整 Git 跟踪源码、测试、固定模型下载清单、两平台构建脚本、许可证、维护记录及本次交接工单。
- **不含**模型权重、用户扫描/识别结果/阅读笔记、原始验证截图和日志、账户凭据、`.env`、`.git`、依赖目录、备份、运行时及安装器。`.env.example` 是占位示例；`backend/models/*.json` 是公开模型哈希清单，不是权重。
- 原始私有证据不随包外发；已提交文档提供脱敏结论、证据 hash 和复现入口。缺失原始证据时不得声称接手者已亲自复核。
- 历史安装包只从 [官方 Releases](https://github.com/cpcboy/ximo-ocr/releases) 获取；不会随本次交接重复发布。

## 收到后怎样用

1. 先核对随包 `.sha256`：macOS 用 `shasum -a 256 <实际ZIP路径>`；Windows PowerShell 用 `Get-FileHash -Algorithm SHA256 <实际ZIP路径>`。尖括号必须替换为实际文件，不能原样执行。
2. 解压到全新目录，打开本文件。不要双击根目录历史 `.command` 脚本来“试一下”：它们可能启动服务或影响本机现有实例。
3. ZIP 用于离线阅读和核对源码；正式开发按详细说明重新 clone。没有 Git 历史会使来源检查和基准 `--reference-commit` 失效，不通过 `git init` 制造假历史。
4. 请先把本入口和工单给 DeepSeek；无需把模型或个人扫描文件上传给对方。

本次交接不会更改已安装 App、公开 Release 或用户数据；代码回退使用 revert PR，不能 force reset 远端。后续部署与回滚必须逐次按维护铁律执行。
