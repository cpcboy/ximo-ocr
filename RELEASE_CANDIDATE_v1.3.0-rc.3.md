# 墨析 1.3.0-rc.3 · Mac Unlimited-OCR 2.0 候选预览版

本候选**仅面向 Apple Silicon Mac，非正式版、非 Latest**。支持 macOS 14及以上；不支持 Intel Mac，也不提供新的 Windows 包。Windows 的已有rc.2仍使用1.0模型，未升级为2.0。

## 主要变化

- Unlimited-OCR 2.0原精度BF16模型，使用内置MLX/Metal推理，无需预装LM Studio。固定模型为`mlx-community/Unlimited-OCR-2-bf16`，修订`850d1e483f5a82a0597f0a45aac31b07ba840df2`。
- 模型单独下载到应用管理目录，不随DMG打包。首次打开后点击“下载模型”，约6.7GB，支持暂停/继续和完整校验。升级保留原1.0模型，不自动覆盖或删除。
- 新2.0识别与阅读去重保留编号、金额和符号差异；保留生成循环保护、原始输出及明确的部分结果提示。不批量修改已有扫描结果。
- 包含此前的多模型接口、并行任务与阅读器修复。使用自定义远程接口会把当前页图像发往所选接口；选择“本机 MLX · 串行”则使用本地2.0。

## 下载与安装

本次附件只有Mac DMG及其SHA-256校验文件。App内部版本为**1.3.0(9)**，不是“墨析2.0”；2.0指OCR模型版本。

安装前退出旧墨析并保留旧App副本。打开DMG，将墨析拖入“应用程序”；不要删除应用支持目录中的扫描、笔记、接口配置或旧模型。模型下载建议至少预留8GB，并额外保留App安装和备份空间。模型就绪后，新建扫描选择“本机 MLX · 串行”。

**App为ad-hoc签名，未获Apple Developer ID公证。** 无法保证Gatekeeper或第三方安全软件放行；若出现安全拦截请停止，不关闭防护或绕过警告。校验文件只能核对完整性，不等于Apple安全认证。

在下载目录执行：

```sh
shasum -a 256 -c MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg.sha256
```

## 本批次来源与校验

- 包源/tag：`ee808f671712e8795c89a4d4f1c1d3f6d6287115`（[PR #19](https://github.com/cpcboy/ximo-ocr/pull/19)合并源）。后续文档提交不改变包源。
- [PR CI](https://github.com/cpcboy/ximo-ocr/actions/runs/40559179370)与[main CI](https://github.com/cpcboy/ximo-ocr/actions/runs/40560077376)均成功；本机178项Python、lint、前端构建及12项Node通过。
- 只读挂载DMG；App20602项清单与构建一致，严格签名、前后端来源、固定MLX适配9文件哈希及许可通过。不含模型权重、用户扫描/笔记/接口密钥或测试环境。

| 附件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg | 527924040 | `0eff500098a1188538673afaca6c86235aec5a0ebacfa32542a178881a689658` |
| MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg.sha256 | 101 | `3629e871c233fc454089d17dbf29aa0a0fed70cb2465977f4887431d2a8a3518` |

## 新DMG实际验收与边界

在M3 Max/36GB、macOS27.0.1直接运行只读DMG中的App，采用全新隔离数据目录：无模型提示与2.0下载入口、系统文件框批量选3页合成PDF及120条小字图片、真实MLX扫描、深色表格阅读、搜索最后一条记录、两次系统保存完整ZIP均通过。ZIP的CRC、页数、2.0模型标记、原始输出及非截断/非部分结果标记通过；120条带不同编号和数量的内容完整保留。任务后自动卸载，正常退出后进程与3000/18765端口释放；携带外部Origin的下载请求被403拒绝（接口边界测试）。

验收复用已完整校验的隔离2.0模型，本批次未重新下载全量6.7GB权重。不宣称全新Mac、最低macOS14实机或169页教材全量质量已验收，也未验收Windows2.0、Intel Mac、跨页联合DASH及正式性能基准。OCR可能漏字或产生错误，重要结果请对照原图校对。本次分发未再次更新本机App，现有扫描、笔记、接口配置及新旧模型内容/权限核对不变。

保留**三类非阻断诊断观察**，不声称零告警或根因已修复：OCR服务退出时的1 semaphore清理告警；原生sandbox文件诊断；本批次两轮正常退出出现的`IMKCFRunLoopWakeUpReliable`消息通道诊断。关键路径已完成，原因仍待后续排查。单元测试依赖弃用、构建工具弃用提示也不等于兼容性全量保证。

## 回退

保留旧App及全部用户数据；遇到候选问题正常退出后恢复自己的旧App副本，不删除模型或扫描目录。旧rc.2下载仍保留，但不含2.0；恢复rc.2会恢复旧模型路线。异常发行会醒目标记撤回，保留原tag与附件供审计，不覆写历史包。

[项目源码](https://github.com/cpcboy/ximo-ocr) · [2.0本机基线](https://github.com/cpcboy/ximo-ocr/blob/main/UNLIMITED_OCR2_VALIDATION.md) · [rc.3验证记录](https://github.com/cpcboy/ximo-ocr/blob/main/RC3_VALIDATION.md) · [维护和回滚](https://github.com/cpcboy/ximo-ocr/blob/main/DEPLOYMENT.md)
