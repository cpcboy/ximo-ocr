# 1.3.0 候选交接：只合并与制包，未发布生产

验收日期：2026-10-21 至 2026-10-22（America/Los_Angeles）。以下主体记录首次阶段交付：源码经 PR 合并、生成候选安装包，未创建正式 GitHub Release、未更新 `/Applications`。全量模型 OCR 和 Windows 目标机仍未验收。

2026-10-22 后续授权：用户明确要求“先发布候选预览版”，允许仅将下列原包作为 `v1.3.0-rc.1` 的 GitHub Pre-release 分发，不设 Latest、不更新本机。流程和限制见 [DEPLOYMENT.md](DEPLOYMENT.md) 与 [候选发行说明](RELEASE_CANDIDATE_v1.3.0-rc.1.md)；实际公开与下载回读结果待执行后补录。

## 源码与候选文件

- 维护文档：[PR #1](https://github.com/cpcboy/ximo-ocr/pull/1)，独立提交 `0f4828e831c124422c264932a296029deea91aa7`，消息为 `docs: 建立维护铁律与执行规范`。
- 功能：[PR #2](https://github.com/cpcboy/ximo-ocr/pull/2)，合并提交 **`2db71b41864cdc3ec3222279f4cf07f2a875e459`**。以下候选均来自这个干净、已合并提交，内含相同 `SOURCE_COMMIT`；文档后续回填不改写既有候选的来源标记。
- [PR CI 39736384496](https://github.com/cpcboy/ximo-ocr/actions/runs/39736384496) 和 [合并后 CI 39736916274](https://github.com/cpcboy/ximo-ocr/actions/runs/39736916274)：Linux/Windows 均成功，Windows 原生 EXE 构建通过。

| 本机候选路径 | 大小（字节） | SHA-256 |
| --- | ---: | --- |
| `build/macos/output/MoxiOCR-macOS-arm64-1.3.0.dmg` | 282807743 | `88bbbd46861df2e2223dc6bacd1841d85742d63a3548200da30f193ae3755cd7` |
| `build/windows/output/MoxiOCR-Windows-x64-1.3.0-candidate.exe` | 52749128 | `d01c1701e741ad911218becd1848f2083224f9f4ca1e6bf2d1eccae2f38b14a6` |

两个文件旁均有 `.sha256`。上述 Windows 文件是 Mac 本机交叉构建产物；同源码也已在 Windows CI 原生构建成功，但本机下载 CI 产物曾网络超时，不把两种构建的文件哈希混为一谈。GitHub Actions 的 `windows-candidate` 是另一个产物，保留期 7 天，不是正式 Release。

Mac 仅适用于 Apple Silicon/macOS 14+；Windows 候选面向 Windows 10 x64，图片 OCR 需要 NVIDIA 显卡。两包均不带模型；界面按平台下载对应模型。Mac 为 ad-hoc 签名、未经 Developer ID 公证；Windows 未商业签名，未通过目标杀毒软件验收。不要关闭防护或添加排除来代替检查。

## 文件变更与原因

本仓库此前没有应用代码，PR #2 含既有项目首次导入；[完整文件清单与 diff](https://github.com/cpcboy/ximo-ocr/pull/2/files) 可逐项审计。核心改动如下：

| 文件/目录 | 目的 |
| --- | --- |
| `backend/model_download.py`、`model_catalog.py`、`models/`、`config.py`、`engine.py`、`app.py` | 分平台模型目录、固定修订/完整性、暂停续传、互斥及经确认的本机来源拦截。 |
| `app/page.tsx` | 首次下载引导、进度/暂停/继续/修复及平台限制说明；保留阅读器。 |
| `mac-app/`、`windows/` | 便携运行时、来源标记、候选打包；Mac 最低系统与 Windows 路径/中文编码修复。 |
| `scripts/`、`tests/`、`.github/workflows/`、`.gitattributes` | 来源/许可/部署检查、跨平台回归及 CI；固定许可 LF 防止哈希变化。 |
| `LICENSE`、`THIRD_PARTY_NOTICES.md`、`third-party/licenses/` | 用户确认的 AGPL-3.0-only 和依赖许可材料。 |
| `README.md`、`CHANGELOG.md`、`DEPLOYMENT.md`、Windows 交接文件 | 用法、影响面、发布边界、实机测试及回滚。 |
| `AGENTS.md`、`MAINTENANCE_RULES.md`、`MODEL_DOWNLOAD_VALIDATION.md`、本文件 | 强制维护入口、七项确认、六步记录、真实证据及未完成项。 |

独立 review 的发现与修复逐条记录于 `MODEL_DOWNLOAD_VALIDATION.md`；末轮代码/打包 review P0/P1/P2=0。采用 code-review / deploy-checklist 的检查口径，明确区分构建、候选验收和生产发布；不是安全/法律认证。

## 本轮已验证

- 本机 57 项 Python、7 项前端/来源/许可测试和 lint 通过。NSIS 用中文/空格目录真实编译；Windows CI 安装 NSIS 后补跑两项编译测试。
- DMG 镜像校验成功；只读挂载后 App 与构建目录完整文件清单一致，签名在真实操作前后均通过 `codesign --verify --deep --strict`。
- 从只读 DMG 运行 App，使用隔离验证目录：打开模型卡 → 继续先前部分下载 → 显示约 5% → 暂停；打开合成 TXT 阅读器 → 原生保存完整 ZIP，页面保留正常；退出后 3000/18765 无监听，后端正常 shutdown。
- 完整 ZIP 的 4 个条目 CRC 全通过，SHA-256 `9fb16067ee8bb90231a07da12e6670e88812b4e15b692e8483e570c123a4a988`。这是合成文本直接读取，不算模型图片 OCR。
- 外部 Origin POST 返回 403，App 的正常下载/阅读/导出操作通过。
- Windows 候选解包 3274 文件完整，`SOURCE_COMMIT` 与前端 `BUILD_SOURCE.json` 均为上述合并提交，`dirty=false`；中文安装说明/卸载器、无扩展名许可/来源文件存在。
- 包内项目 LICENSE 与仓库一致，前端包含 509 项依赖许可索引；检查未发现模型权重、用户任务、扫描原件、日志或凭据。

本机证据目录（不提交 Git）：`test-results/model-download-20261021/`。

| 证据 | 内容 |
| --- | --- |
| `01-paused.png`、`02-resumed.png` | 首轮真实下载/暂停/续传。 |
| `03-native-import-reader.png`、`04-export-workspace-retained.png` | 原生文件选择、阅读、完整包保存。 |
| `05-merged-dmg-model.png`、`06-merged-dmg-resumed-paused.png` | 合并版只读 DMG 启动与暂停续传。重开后先显示本轮 0，点击继续校验后恢复已缓存进度。 |
| `07-merged-dmg-reader.png`、`08-merged-dmg-export-retained.png` | 合并候选阅读、完整导出后页面正常。 |
| `merged-logs/`、`merged-app.log`、`Moxi-merged-2db71b4-export.zip` | 后台日志、系统诊断与合成导出文件。 |

## 未完成项与生产状态

1. 全量约 6.7 GB 模型尚未完成下载，因此完整文件校验收据、真实图片/PDF OCR、加载/卸载后的内存释放仍需继续验收；现保留部分下载，已暂停、App 已退出。
2. Windows 目标电脑安装、杀毒、完整运行库/模型下载、NVIDIA OCR、退出显存释放尚未实测。按 `WINDOWS_TEST_REPORT_TEMPLATE.md` 执行，不能以 CI 代替。
3. Mac 前后端日志未检出 Traceback/ERROR/Exception；原生 App 仍出现一条 `sandbox_extension_issue_file failed for : 2 (No such file or directory)`。本轮导出成功，但该系统诊断根因未证实，正式验收需复查，不声称所有日志无异常。
4. 遗留 Cloudflare 示例的 `tsc --noEmit` 类型错误未解决，不作为通过项。CI 有 Actions Node 20 及 runner 迁移提示；Mac 构建有 Transformers 无 PyTorch/TF/Flax 提示（使用 MLX）和 hdiutil 弃用提示；不隐藏这些输出。
   本机 Windows 交叉构建的 pip 还报告构建用开发环境中 Torch 2.13.0 与 setuptools 65.5.0 的依赖冲突；目标 bootstrap 安装及编译退出 0，解包未包含这两项开发环境依赖。同源码在隔离 Windows CI 构建通过，但这仍不替代目标机运行库和 OCR 验收；未擅自修改开发环境来消除提示。
5. 仅运行并退出隔离候选；生产 `/Applications/墨析 OCR 工作台.app` 仍为 **1.2.2 build 5**，与维护开始清单一致，未替换、未重启生产、未迁移业务数据、未创建正式 Release。

## 回滚与后续

本次未部署生产，无需回滚已安装应用。旧版 App、维护前清单及源码归档仍在忽略的 `.maintenance-backups/2026-10-21-model-download/`，旧 App 的严格签名验证通过；不要将备份或测试数据上传 Git/Release。

源码撤回只能走 revert PR。后续正式更新必须重新从最新已合并 clean main 构建，完成上述验收、确认本机无漂移，再按 `DEPLOYMENT.md` 的 snapshot/install 执行；失败用保留的旧 App 和清单执行 rollback，不覆盖用户模型和识别数据。本次没有执行 install/rollback。
