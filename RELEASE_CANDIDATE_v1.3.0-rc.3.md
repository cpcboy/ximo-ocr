# 墨析 1.3.0-rc.3 · Mac Unlimited-OCR 2.0 候选预览版

本候选**仅面向 Apple Silicon Mac，非正式版、非 Latest**。支持 macOS 14及以上；不支持 Intel Mac，也不提供新的 Windows 包。Windows 的已有rc.2仍使用1.0模型，未升级为2.0。

## 主要变化

- Unlimited-OCR 2.0的原精度BF16模型，使用内置MLX/Metal推理，无需预装LM Studio。固定模型为`mlx-community/Unlimited-OCR-2-bf16`，修订`850d1e483f5a82a0597f0a45aac31b07ba840df2`。
- 模型单独下载到应用管理目录，不随DMG打包。首次打开后点击“下载模型”，约6.7GB，支持暂停/继续和完整校验。升级保留原1.0模型，不自动覆盖或删除。
- 新2.0识别与阅读去重保留编号、金额和符号差异；保留生成循环保护、原始输出及明确的部分结果提示。不批量修改已有扫描结果。
- 包含此前的多模型接口、并行任务与阅读器修复。使用自定义远程接口会把当前页图像发往所选接口；选择“本机 MLX · 串行”则使用本地2.0。

## 下载、安装与校验

本次附件只有`MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg`及其`.sha256`校验文件。App内部版本为1.3.0(9)，不是“墨析2.0”；2.0指OCR模型版本。实际包源提交、文件大小和SHA-256附在发行页面的本批次构建信息中。

安装前退出旧墨析并保留旧App副本。打开DMG，将墨析拖入“应用程序”；不要删除应用支持目录中的扫描、笔记、接口配置或旧模型。模型下载除6.7GB权重外还需要App和临时/回退空间，建议至少预留8GB用于新模型，并额外保留安装/备份空间。已有用户的模型就绪后，新建扫描选择“本机 MLX · 串行”。

在下载目录执行`shasum -a 256 -c MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg.sha256`可核对文件。校验不等于Apple安全认证。

## 验证范围与已知限制

- 2.0本机基线已在M3 Max/36GB、macOS27.0.1完成六类合成图、三页PDF、120条小字、阅读搜索/表格、完整ZIP和自动卸载测试。该结果不是全数据集精度承诺，也不是最低macOS14或全新机器验收；本次新DMG的实际结果以[rc.3验证记录](https://github.com/cpcboy/ximo-ocr/blob/main/RC3_VALIDATION.md)为准。
- **App为ad-hoc签名，未获Apple Developer ID公证。** 无法保证Gatekeeper或第三方安全软件放行；若出现安全拦截请停止，不关闭防护或绕过警告。
- 保留两项非阻断观察：OCR服务退出时可能出现1 semaphore清理告警；原生控制台可能出现sandbox文件诊断。此前任务/导出/卸载和服务退出已通过，但没有宣称根因解决。
- 暂未验收Windows2.0、Intel Mac、最低macOS14实机、169页教材/任意复杂扫描全量质量、跨页联合DASH及正式性能基准。OCR可能漏字或产生错误，重要结果请对照原图校对。

## 回退与来源

保留旧App及全部用户数据；遇到候选问题正常退出后恢复自己的旧App副本，不删除模型或扫描目录。仓库旧rc.2下载仍保留，但不含2.0；恢复rc.2会恢复旧模型路线。

[项目源码](https://github.com/cpcboy/ximo-ocr) · [2.0本机基线验证](https://github.com/cpcboy/ximo-ocr/blob/main/UNLIMITED_OCR2_VALIDATION.md) · [本次验证](https://github.com/cpcboy/ximo-ocr/blob/main/RC3_VALIDATION.md) · [维护和回滚](https://github.com/cpcboy/ximo-ocr/blob/main/DEPLOYMENT.md)
