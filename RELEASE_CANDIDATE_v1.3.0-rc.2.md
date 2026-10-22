# 墨析 1.3.0-rc.2 · 阅读器修复候选预览版

**Pre-release，非正式版、非 Latest。** 本批次将已合并的阅读器配色修复打入 Mac 和 Windows 新安装器；保留 rc.1 的 tag/资产，不覆盖历史文件，不自动更新现有应用或用户数据。

## 本次变化

- 修复深色阅读正文“白底浅字”：局部映射正文、表格、代码、引用的颜色，不影响工作台主题。
- 延续 App 内按平台下载模型：Mac Apple Silicon 使用 Unlimited-OCR MLX；Windows 使用 baidu/Unlimited-OCR NVIDIA/PyTorch。安装包不含模型或用户扫描数据。
- 新安装文件名独立带 rc.2；Mac 应用版本 1.3.0 build 7，Windows 文件数值版本 1.3.0.2 / 显示版本 1.3.0-rc.2。不是自动升级机制。

## 下载与限制

| 平台 | 文件 | 要求 |
| --- | --- | --- |
| Mac | `MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg` | Apple Silicon、macOS 14+；ad-hoc 签名，未 Developer ID 公证 |
| Windows | `MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe` | Windows 10 x64，图片 OCR 需要 NVIDIA/CUDA；未商业签名、未完成目标机杀毒验收 |

各下载同名 `.sha256`；Mac 使用 `shasum -a 256 <文件>`，Windows 使用 `Get-FileHash <文件> -Algorithm SHA256` 核对。系统或杀毒软件拦截时停止并保留告警，不关闭安全检查、不加排除。旧 rc.1 浏览器下载曾遇到拦截/等待问题，本批次必须重新记录，不能继承为通过。

## 验证边界

源码阶段 57 Python、lint、构建及 11 Node 测试已通过；CI、合并、打包和本批次实测结果在发布前/后分别核对并回填 [RC2_VALIDATION.md](https://github.com/cpcboy/ximo-ocr/blob/main/RC2_VALIDATION.md)。既有本机修复版的四主题、文件选择、合成 TXT、ZIP 导出验证不是新 DMG 的验收，也不是 Windows 实机验收。

全量约 6.7 GB 下载、真实图片/PDF OCR、模型加载后内存释放、Windows 真实安装与显存释放仍未完成验收。Mac 既有 `sandbox_extension_issue_file failed for : 2` 诊断和 Cloudflare 示例类型检查遗留问题未宣称修复。TXT 直接导入不算模型 OCR。

## 来源与回退

仅从本次 PR 合并后通过 main CI 的 clean main 构建，tag 必须等于两包内 `SOURCE_COMMIT`。实际 SHA、文件大小/哈希会在公开前追加到发行说明；缺失或不一致时禁止公开。不以之后的证据文档提交替换包来源。

出现来源/哈希错误、错误正式标识或关键路径失败时停止公开；已经公开则标记撤回、保留原 tag/包，通过新的修复 PR 另发候选，不覆盖资产。安装前保留旧 App/安装器；回装时只换程序，不删除扫描或模型目录。rc.1 仍有已知阅读缺陷，不把回退到它称为修复。
