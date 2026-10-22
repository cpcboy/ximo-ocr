# 1.3.0 模型下载与安装候选验证

日期：2026-10-21 至 2026-10-22。结论：**本次按用户确认交付 PR 合并及候选包，正式发布延期**。本记录刻意区分代码 review、候选构建、真实界面操作和全量模型 OCR；不能互相替代。生产更新必须在后续全量验收通过后进行。最终来源、安装包哈希与合并后实测见 [CANDIDATE_DELIVERY.md](CANDIDATE_DELIVERY.md)。用户于 2026-10-22 追加授权候选 Pre-release 分发，不改变本记录的未验收结论；见 [候选发行说明](RELEASE_CANDIDATE_v1.3.0-rc.1.md)。

**后续状态说明：** 本文下列 1.2.2、未安装/未发布描述保留为首次验证阶段事实。之后已公开候选预览版并按第 9 项授权试装本机 1.3.0 (6)，数据保全/导出通过，但深色阅读视觉失败，已回退；用户第 10 项授权修复后重新更新，见 [LOCAL_PREVIEW_UPDATE.md](LOCAL_PREVIEW_UPDATE.md)。不将试装计为整个更新、全量模型、Windows 或正式版验收；既有原生 sandbox 诊断仍待复查。

## 范围与隔离

- Apple Silicon Mac 上构建、运行 `build/macos/墨析 OCR 工作台.app`，使用独立临时 support 目录，并设置 `OCR_STUDIO_DISABLE_LEGACY_MODEL=1`，没有读取用户扫描任务。
- 已安装 `/Applications/墨析 OCR 工作台.app` 仍是 1.2.2 build 5，没有替换或启动生产版本，没有修改生产数据。
- 旧 App、完整清单、原始源码在忽略的 `.maintenance-backups/2026-10-21-model-download/`；原始源码归档 SHA-256：`d5674b753bbcfe2cc307e8f54fa55d2a04d246635dd0570f2dfeddf69090ea05`。
- Mac 下载官方固定修订 `LoJexLLM/Unlimited-OCR-MLX@267d7adcbcd3730fdffb1eefd70ef6f486fbfc92`，12 文件共 6,682,782,881 字节。模型不进入 Git/安装包。
- Windows 为 `baidu/Unlimited-OCR@07dea832e22aefee32ad281d4b80551282e1c168`，不是 MLX；此次没有安装到家中电脑。

## 独立对抗 review

| 级别 | 问题 | 处理与证据 |
| --- | --- | --- |
| P1 | 外部网页可触发本机大文件下载 | 用户确认后加入 Host/Origin/Referer/Fetch Metadata 校验，不扩大 CORS；正常 App 点击成功，外部 Origin POST 实测 403；回归测试覆盖边界。 |
| P1 | Swift 隐式使用新系统最低版本 | 显式目标 `arm64-apple-macosx14.0`；候选 `vtool` 显示 minos 14.0，MLX wheel 按 macOS 14 解析。 |
| P2 | 损坏完成收据可能使健康接口报错 | 收据类型检查和异常容错，合成测试通过。 |
| P2 | Windows 只凭标记判定运行环境成功，修复可能漏装 | 真实导入/版本/路径探针、版本化标记、失败强制重装；合成测试通过，Windows 实机待验。 |
| P2 | Windows 测试误用 Unix 可执行位 | 仅非 Windows 检查执行位，文件存在性仍跨平台检查。 |
| P2 | 打包可能引用旧前端或未提交源码 | 源码摘要、dirty 标记、前后双校验、发布 clean/main 门禁；合成测试通过。 |
| P2 | 历史验证文档包含真实任务标识与备份信息 | 原文留本机备份；公开文档脱敏，不提交扫描资料。 |
| P2 | 五个实际前端运行依赖没有顶层许可文件，被收集器静默跳过 | 增加固定来源/哈希补充及实际运行依赖缺项阻断；缺项、补充、篡改测试通过；独立联网核对原文与模板，复核清零。 |
| P2 | Windows Git 将固定许可文本换为 CRLF，首次 CI 哈希校验失败 | `.gitattributes` 仅对固定许可文本强制 LF；保留逐字节 SHA-256 校验，新增 Windows 风格检出测试。独立对照证明规则前后三文件的哈希差异，review 清零；第二轮 Windows 前端构建及 7 项测试通过。 |
| P2 | 第二轮 Windows 原生 NSIS 的混合路径分隔符导致 File 找不到文件，且输入编码为 ACP | 两平台分别传原生 `STAGE_FILES`，显式 UTF-8；新增两项真实 NSIS 编译测试。独立复核 P0/P1/P2=0；7-Zip 确认无扩展名、中文/空格文件和中文卸载器入包，Windows CI 继续重跑。 |

末轮独立代码及许可补充复核结论：P0/P1/P2 = 0。独立收集 509 项依赖，五个原缺项均生成 LICENSE 与 SOURCE.json；实际运行依赖无许可材料缺项。这是工程 review，不是法律合规认证，也不是未完成平台的实机验收。

## 已执行检查

- Python：57 项通过，包括下载、完整性、暂停/恢复、互斥、本机 API 拦截、读取状态、重复保护、Windows 启动器、两项 NSIS 真实编译和部署器。没有 NSIS 的首轮 CI 环境会跳过两项，Windows 安装 NSIS 后单独补跑。PyMuPDF 有 5 条 SWIG 废弃警告，不是运行异常。
- `npm run lint` 通过；`npm test` 最终 7 项页面/来源/许可/Windows 检出测试通过。
- `npx tsc --noEmit` **未通过**：遗留 Cloudflare 示例缺少 `cloudflare:workers`、`Fetcher`、`D1Database` 类型，不作为本次已通过项。未通过删除示例或放宽类型检查掩盖。
- Mac 候选 App 构建成功（约 539 MB），`codesign --verify --deep --strict` 通过；这是 ad-hoc 签名，不是 Developer ID 公证，也不是干净 macOS 14 实机验收。
- 首次 Windows 交叉构建 EXE 成功（52,710,268 字节），旧候选已归档；后续修复/许可变更后必须重新构建。PR #2 首轮 CI（run 39734583701）Linux 成功，Windows Python/lint 通过但前端构建因 CRLF 许可哈希失败；第二轮（run 39735172608）Windows Python/lint/7 项前端测试均通过，原生 NSIS 编译因混合路径失败。已分别修复、独立 review 后补交同一 PR，继续重跑。不隐藏失败记录，目标 Windows 10/NVIDIA 仍未验收。
- 打包目录扫描未发现模型权重、扫描任务、运行日志；最终新包仍需重复检查。

## 真实 Mac 用户路径

| 路径 | 实测结果 |
| --- | --- |
| 无模型启动 | App 可打开，显示首次下载提示、Mac 模型名/修订/保存目录；没有预加载模型。 |
| 点击下载 | 由 App 按钮发起官方固定模型请求，状态和字节数变化。 |
| 暂停 / 继续 | 显示“继续下载”，恢复后继续传输，保留 `.part`。 |
| 下载中退出 / 重开 | 正常退出后 Node/Python 及 3000/18765 监听停止；重开显示发现未完成下载，点击可续传。 |
| 原生选择文件 | 系统 NSOpenPanel 可打开；选中仓库合成 `file-picker-smoke.txt` 后成功导入并显示 1 页完成。 |
| 阅读 | 点击“阅读”，可显示测试文字及阅读器导航。纯文本直接读取，不算模型 OCR。 |
| 完整包导出 | 原生保存框成功保存 ZIP，工作台未被下载导航替换；`unzip -t` 四项文件均通过，包含源 TXT、结果 TXT/MD/JSON。 |
| 外部来源 | 独立外部 Origin 请求返回 403；上述正常 App 路径没有被拦截。 |

本机证据在忽略目录 `test-results/model-download-20261021/`：`01-paused.png`、`02-resumed.png`、`03-native-import-reader.png`、`04-export-workspace-retained.png`。截图只包含合成测试和模型状态，不公开系统文件框里的用户文件列表。

原生导出合成 ZIP SHA-256：`acd3dda45418a91d6512e4f9a91784d76a10a94c68f3d2cb34cd2e3a0e1e15aa`。该 ZIP 为本机验证产物，不是安装包，不上传 Release。

本轮结束前通过 App 暂停下载，保留约 334 MB 的下载进度，再正常退出。3000 / 18765 无监听，后端记录正常 shutdown，前后端日志未检出 Traceback/ERROR/Exception。App 自身 stderr 曾有一条系统诊断 `sandbox_extension_issue_file failed for : 2 (No such file or directory)`；文件选择/导出已成功，但该诊断原因尚未证实，不将日志表述为完全无异常，后续正式验收需复查。

## 验收与发布门禁状态

1. 约 6.7 GB 全量 MLX 权重尚未下载完成；当时官方下载速度约 100–200 KB/s，仅验证了实际部分传输、暂停/续传。尚未验证完整哈希收据、全量模型加载和真实图片/PDF OCR，不得宣称“下载后即可用”已验收。
2. 本机回归、许可复核及公开源码检查已完成；PR #2 已合并为 `2db71b41864cdc3ec3222279f4cf07f2a875e459`，PR 第三轮 CI 39736384496 和合并后 CI 39736916274 均成功，合并后候选已重建并复验（见候选交接）；不是生产发布。
3. Windows 真实安装、杀毒、Edge 已有实例、完整模型/运行库下载、NVIDIA OCR、退出显存释放需目标电脑验收，见 Windows 交接文件。
4. 没有发布 GitHub Release，没有替换生产 App；生产仍为 1.2.2。只有满足 `DEPLOYMENT.md` 门禁后才能更新本机。

回滚：当前无需回滚生产。后续部署只恢复旧 App，不碰用户数据与模型；使用完整清单校验和 `scripts/deploy_macos.py rollback`，详见 `DEPLOYMENT.md`。
