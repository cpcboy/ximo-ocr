# 墨析 1.3.0-rc.1 · 候选预览版

这是供测试的 **Pre-release，不是正式生产版本**。全量模型下载、真实图片/PDF OCR、模型加载/卸载内存释放以及 Windows 目标机验收尚未完成；请勿把“已提供下载”理解为“已完成实机验收”。本次只分发安装包，不自动更新本机或远端电脑。

**已公开预览，但浏览器分发验收未全部通过（2026-10-22 实测）：** 当前测试用 Chrome 在点击 Windows EXE 后显示 `ERR_BLOCKED_BY_CLIENT`；未证明是文件恶意、扩展拦截或其他原因，也未尝试放行/绕过。Mac 大文件浏览器等待超时，未确认完整浏览器下载成功。发行页和 Mac 校验清单的真实浏览器路径已验证；两个安装包及两个清单的独立公开下载均完整回读、SHA-256 一致，但这不能代替浏览器、安全软件或安装验收。遇到拦截请停止测试并保留告警，不关闭防护。

## 下载哪个文件

| 平台 | 安装文件 | 要求与签名状态 |
| --- | --- | --- |
| Apple Silicon Mac | `MoxiOCR-macOS-arm64-1.3.0.dmg` | M 系列芯片、macOS 14+；ad-hoc 签名，未经 Developer ID 公证。Intel Mac 不适用。 |
| Windows 10 x64 | `MoxiOCR-Windows-x64-1.3.0-candidate.exe` | 图片 OCR 需要 NVIDIA GPU/兼容 CUDA 12.8 的驱动；未商业签名、目标杀毒软件尚未验收。 |

在此发行页下方 Assets 下载对应安装器和同名 `.sha256`，不要把 Source code ZIP 当成安装包。若系统或杀毒软件拦截，请保留告警并停止安装供检查；不要关闭防护或添加排除来代替验证。测试前保留原安装包和扫描数据备份；不建议覆盖日常使用环境。

两个安装包都不包含模型。安装后由用户点击下载：Mac 为 `LoJexLLM/Unlimited-OCR-MLX`，Windows 为 `baidu/Unlimited-OCR` NVIDIA/PyTorch；Windows 不使用 Apple MLX。约 6.7 GB 权重下载与运行组件需联网，Office 转换另需 LibreOffice。

## 本版内容与验证边界

- 新增 App 内分平台模型下载、暂停/续传、固定修订和内容校验、状态/修复入口；保留阅读器和完整结果包导出。
- 候选源码已通过 57 项 Python、7 项前端/来源/许可测试、lint 和 Linux/Windows CI；Windows 原生安装器构建通过。
- Mac 实测到部分模型下载/暂停/退出/续传、合成 TXT 导入/阅读/完整 ZIP 导出、退出后服务停止。TXT 直接读取 **不是模型 OCR 验收**。
- 尚未验证完整权重校验、模型实际加载、图片/PDF OCR及模型占用内存释放；Windows 真实安装、杀毒、完整运行组件、NVIDIA OCR 和显存释放均待验收。
- Mac 原生窗口曾记录 `sandbox_extension_issue_file failed for : 2`，导入/导出实际成功，但诊断原因未证实。遗留 Cloudflare 示例的 `tsc --noEmit` 也未通过；完整边界见仓库的候选验收文档。

## 来源与完整性

发行 tag `v1.3.0-rc.1` 固定指向两包的实际构建来源：[`2db71b41864cdc3ec3222279f4cf07f2a875e459`](https://github.com/cpcboy/ximo-ocr/commit/2db71b41864cdc3ec3222279f4cf07f2a875e459)，已由 [PR #2](https://github.com/cpcboy/ximo-ocr/pull/2) 合并，[main CI](https://github.com/cpcboy/ximo-ocr/actions/runs/39736916274) 成功。应用内版本为 1.3.0；rc.1 是此候选分发批次名，不暗示应用二进制已更新。

Mac DMG 是本机 Apple Silicon 构建；以下 Windows EXE 是 Mac 交叉构建，同源 Windows CI 也构建成功，但两种产物不是同一个二进制。本次没有重新打包，后续文档提交不冒充包内来源。

| 文件 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `MoxiOCR-macOS-arm64-1.3.0.dmg` | 282807743 | `88bbbd46861df2e2223dc6bacd1841d85742d63a3548200da30f193ae3755cd7` |
| `MoxiOCR-Windows-x64-1.3.0-candidate.exe` | 52749128 | `d01c1701e741ad911218becd1848f2083224f9f4ca1e6bf2d1eccae2f38b14a6` |

Mac 在下载目录执行 `shasum -a 256 MoxiOCR-macOS-arm64-1.3.0.dmg`；Windows PowerShell 执行 `Get-FileHash .\MoxiOCR-Windows-x64-1.3.0-candidate.exe -Algorithm SHA256`，与上表/同名清单核对。哈希匹配只能证明与此发布文件一致，不代表杀毒或功能验收通过。

源代码按 AGPL-3.0-only 发布；第三方库和模型保留各自许可。安装器不含用户扫描原件、OCR 结果、模型权重或凭据。

## 回退与反馈

本次未替换现有 App，无需对其回滚。若自行测试安装后需回退，正常退出后恢复事先保留的旧 App/安装包，不删除或覆盖模型、扫描结果和笔记目录。发现源/哈希不符、错误验收宣传或安装风险时停止使用并反馈；发行维护者将标记撤回，修复经 PR 后另发新 rc，不覆盖本版资产或改写 tag。

候选证据与后续状态见仓库 main 的 [CANDIDATE_DELIVERY.md](https://github.com/cpcboy/ximo-ocr/blob/main/CANDIDATE_DELIVERY.md)；这不改变此版本固定的源码和文件哈希。
