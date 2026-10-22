# 墨析 1.3.0-rc.2 · 阅读器修复候选预览版

**Pre-release，非正式版、非 Latest。** 本批次将已合并的阅读器配色修复打入 Mac 和 Windows 新安装器；保留 rc.1 的 tag/资产，不覆盖历史文件，不自动更新现有应用或用户数据。

已于2026-10-22公开 [v1.3.0-rc.2](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.2)。两包与tag固定来源 **`3e9a7e2ea2bc33fd58cafd33520a1928599a28c3`**（PR #9），全部文件大小/SHA-256和实际证据见 [RC2_VALIDATION.md](https://github.com/cpcboy/ximo-ocr/blob/main/RC2_VALIDATION.md)。本文件为公开事实回填，不会重建或改写安装包来源。

## 本次变化

- 修复深色阅读正文“白底浅字”：局部映射正文、表格、代码、引用的颜色，不影响工作台主题。
- 延续 App 内按平台下载模型：Mac Apple Silicon 使用 Unlimited-OCR MLX；Windows 使用 baidu/Unlimited-OCR NVIDIA/PyTorch。安装包不含模型或用户扫描数据。
- 新安装文件名独立带 rc.2；Mac 应用版本 1.3.0 build 7，Windows 文件数值版本 1.3.0.2 / 显示版本 1.3.0-rc.2。不是自动升级机制。

## 下载与限制

| 平台 | 文件 | 要求 |
| --- | --- | --- |
| Mac | `MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg` | Apple Silicon、macOS 14+；ad-hoc 签名，未 Developer ID 公证 |
| Windows | `MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe` | Windows 10 x64，图片 OCR 需要 NVIDIA/CUDA；未商业签名、未完成目标机杀毒验收 |

各下载同名 `.sha256`；Mac 使用 `shasum -a 256 <文件>`，Windows 使用 `Get-FileHash <文件> -Algorithm SHA256` 核对。系统或杀毒软件拦截时停止并保留告警，不关闭安全检查、不加排除。旧 rc.1 浏览器下载问题不继承为本批次结论；本批次用户确认使用内置浏览器后，发行页及四文件真实下载均已验证，另以公开URL独立回读校验，不保证Chrome或Windows安全软件兼容性。

| 资产 | 字节数 | SHA-256 |
| --- | ---: | --- |
| MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg | 282825180 | d96cfa4be5218c0056b2115527dd370687e1518b53715c08d1d901e33f1e844b |
| MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg.sha256 | 101 | f42d394d2a74a4299898c6b9ffd7532fcde3cda70abac41a02a8d0c62c40f4c5 |
| MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe | 52748024 | f39679299d48ace609eb9276087c2840f0845789ec7d45fa82c8fcc22172c678 |
| MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe.sha256 | 111 | 0c5e3dd15f08375154de94301ed2aa4f9b4d7fc3616f0afa5a4c7dfedfc41c8c |

## 验证边界

57 Python、lint、构建及11 Node测试和PR/main CI均通过。两包内容/来源/许可/哈希已复核；直接从本次新DMG启动，完成四主题可读性、文件选择取消/重开、合成TXT、ZIP保存和正常退出验证，原扫描/模型哈希未变。公开Windows EXE为Mac交叉构建，Windows CI另一次原生构建成功不是目标机安装验收。公开浏览器与独立回读状态见 [RC2_VALIDATION.md](https://github.com/cpcboy/ximo-ocr/blob/main/RC2_VALIDATION.md)，未完成项不记通过。

全量约 6.7 GB 下载、真实图片/PDF OCR、模型加载后内存释放、Windows 真实安装与显存释放仍未完成验收。Mac 原生sandbox文件/输入法mach-port诊断和 Cloudflare 示例类型检查遗留问题未宣称修复；服务日志无ERROR/Traceback/HTTP5xx不等于零原生诊断。TXT 直接导入不算模型 OCR。

## 来源与回退

已从PR #9合并后通过main CI的clean main构建，实际tag等于两包内 `SOURCE_COMMIT`；公开前核对四资产服务端大小/哈希和已review正文一致。不以之后的证据文档提交替换包来源。证据文档PR合并且CI通过后，仅同步本说明到现有候选发行页，不改变tag、资产、Pre-release或非Latest状态。

出现来源/哈希错误、错误正式标识或关键路径失败时停止公开；已经公开则标记撤回、保留原 tag/包，通过新的修复 PR 另发候选，不覆盖资产。安装前保留旧 App/安装器；回装时只换程序，不删除扫描或模型目录。rc.1 仍有已知阅读缺陷，不把回退到它称为修复。
