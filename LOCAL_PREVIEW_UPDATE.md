# 本机候选预览版更新记录

日期：2026-10-22（America/Los_Angeles）。状态：首次安装 1.3.0 build 6 后，独立复核发现深色阅读对比度失败，已回退至 1.2.2；用户另授权修复后重新更新。不得把首次尝试登记为验收完成。后续修复仍须 PR/CI/合并及原生复验；不是正式版或全量模型 OCR 验收。

## 已确认范围

用户确认：“先备份旧版，再把本机更新到候选预览版，保留所有扫描和模型数据，更新后验证一下。”

首次范围仅本机 `/Applications/墨析 OCR 工作台.app` 从 1.2.2 build 5 更新至 1.3.0 build 6 候选试用，不改代码。首次视觉验收失败后，用户明确追加“修复后再更新并验证”，只扩展为阅读器配色及回归测试修复；不提升 GitHub Release 为正式版，不操作 Windows，不触发全量模型下载，不重扫或编辑历史任务。正式 OCR 验收尚未完成。

## 首次尝试的来源和最小改动

本节及随后“首次更新前检查”“首次备份、构建与安装”为已执行的历史记录，不是再次部署命令，不得复用已存在的 `install/` 或首次参数。第 10 项修复后的新参数以末尾“按追加授权修复并重新验收”为准。

- 公开候选源固定为 `2db71b41864cdc3ec3222279f4cf07f2a875e459`，其 tag 和四个下载资产保持不变。
- 当前部署器要求 `SOURCE_COMMIT == HEAD == origin/main`；本次不放宽此条件，不使用 rollback 模式安装新版本。
- 本次授权文档经独立 review、PR、CI、合并后，从该 clean main 重建本机 App。核对相对候选源只变动文档，应用内如实记录新来源；这个本地重建 App 不声明与公开 DMG 内的二进制完全相同。

## 首次更新前检查

- 当前 App 3736 项文件/链接与 `.maintenance-backups/2026-10-21-model-download/installed-before.json` 一致；旧清单不覆盖。
- 初次只读接口显示 4 个历史任务，均非活动状态；这是辅助信息，不代替磁盘全部任务检查。启动会恢复未完成任务，因此必须确认所有磁盘元数据可读取、ID 与目录名一致，且状态只包含 completed/partial/failed/canceled；其他状态一律阻断。
- 业务数据保持在原应用支持目录的 `data/`，模型继续保留原应用管理目录及旧 LM Studio 模型目录。只读哈希清单在忽略验证目录保存，不把文件名、扫描内容、模型或凭据提交 Git。
- 退出前确认无上传、未保存文本或待保存阅读状态，正常退出并等待保存完成；退出后再次全量检查任务、复查端口和残留进程，随后才建立稳定数据/模型清单。任何非终态任务、未保存编辑、漂移、来源/签名不符均停止，不强制取消任务或覆盖。

## 首次备份、构建与安装（历史记录，勿复用参数）

回退目录位于应用支持目录下的 `maintenance-backups/2026-10-22-local-preview/`，不会因删除 Downloads 而丢失。

1. 构建前保存旧构建 App 到 `prebuild/release-candidate.app`；更新前复制现有 App 到 `preflight/installed-1.2.2.app`，核对文件/链接清单与签名。两份不是业务数据备份，不修改数据本体。
2. 运行已有 `npm run build`、`./mac-app/build-app.sh`。验证本机新 App 版本、来源、签名和源码差异；不运行会覆盖同名发布资产的命令。
3. 安装前独立保存新旧 App 清单。按 `DEPLOYMENT.md` 的原 `install` 入口，使用初次维护基线和未存在的 `install/` 目录。部署器保留 `install/previous.app`、`deployment.json`、`installed-manifest.json`；审计在替换后写入，若命令异常，必须先核对实际已安装 App 和 previous.app 的状态，不盲目重试或重取基线。
4. 先在全新独立支持目录启动已安装 App，不复用旧 PID 文件；每次模式切换前核对两端口空闲/旧进程退出，启动后核对监听 PID、命令和支持目录与本次实例一致，再验证合成 TXT 文件选择/导入/阅读/ZIP 保存、退出及端口关闭。隔离实例清除继承的 `UNLIMITED_OCR_MODEL_DIR`，设置 `OCR_STUDIO_DISABLE_LEGACY_MODEL=1`，不修改全局 launchctl 环境，不下载或加载权重。默认 WebKit 存储仍共享主题/识别选项，不把 support 隔离描述为整个应用零共享，不改这些偏好。
5. 再以正常目录启动，核对首页、模型入口和任务计数；不打开历史阅读器（可能自动写阅读状态）或准备历史预览。再次比较业务/模型文件清单，保持原件、结果、笔记和权重不变。

## 验证边界

这次验证针对“本机候选 App 更新及基本使用路径”，不是无模型首次完整下载、图片/PDF 模型 OCR、已加载模型内存释放或 Windows 实机验收。合成 TXT 直接读取不计为模型 OCR。公开浏览器分发和原生系统诊断的既有待验项仍保留。

真实截图只保存隔离合成任务界面，不发布历史任务文件名；日志仅留本地，公开文档给摘要和状态。数据保全失败、启动/导出/退出失败时不宣称更新完成，停止并回退旧 App。

## 回滚

每次回退先正常退出候选，确认服务端口和进程停止；再确认对应 `previous.app` 与原 3736 项清单相同且签名有效。用原 `scripts/deploy_macos.py rollback`，expected-current 为该次安装审计的 `installed-manifest.json`，backup-dir 必须是全新独立审计目录。首次已执行回退使用 `install/` 内的备份/清单；修复版若再失败，必须使用新 `install-reader-fix/` 内的备份/清单，不能拿首次清单代替。回退不删除/覆盖模型、扫描数据或笔记，也不能恢复任何已发生的业务数据写入，因此不能跳过无活动任务和隔离验证门禁。若当前 App 已漂移或审计缺失，停止核对实际状态，不伪造新基线。回退后真实启动旧版并复查数据清单。

## 实际执行与证据

部署前自查及独立对抗 review 已完成：初轮 2 项 P1（未完成旧任务可能重排、隔离 support 仍共用端口）和 2 项 P2（替换后写审计、WebKit 偏好共享）已落实为上述强制操作门禁，末轮文档 P0/P1/P2=0。57 Python 回归测试通过，旧 App 签名有效；只读遍历磁盘全部 4 个任务为 3 completed / 1 failed，均可解析且 ID 一致。安装前仍须复查，不能用这次检查代替退出后的稳定清单。

### Git、CI 与实际构建

- 授权/操作门禁提交 `b34dfb73bb37d99bcdfe2ae4327d5fdc1745abeb`，经 [PR #6](https://github.com/cpcboy/ximo-ocr/pull/6) 合并为 `c30850d34dc36411923360645f241c976634d082`。
- [PR CI 39797691124](https://github.com/cpcboy/ximo-ocr/actions/runs/39797691124) 与 [main CI 39798654841](https://github.com/cpcboy/ximo-ocr/actions/runs/39798654841) 最终均为 completed/success。GitHub 当时有 [Actions Results 延迟事件](https://www.githubstatus.com/incidents/q29p76qtnkyk)；未用两分项成功替代未结束的汇总，等 main 于 15:01:04 UTC 明确成功后才执行 install。
- 本机新增验证：57 Python、lint、构建后的 7 项前端/来源/许可测试均通过；已运行 `npm run build` 和 `./mac-app/build-app.sh`。保留既有 SWIG 废弃警告、MLX 环境中 Transformers 未安装其他框架的提示，不把提示隐藏为全平台模型验收。
- 首次安装 App 的 `SOURCE_COMMIT` 为 **`c30850d34dc36411923360645f241c976634d082`**，原生“关于”显示 **1.3.0 (6)**。相对公开候选源只有 8 份 Markdown 文档差异；没有应用代码差异。该 App 后因阅读视觉验收失败回退；后续证据文档不改写其来源。
- 没有运行 DMG/Windows 安装器构建入口、没有替换 Release 资产或 tag。公开候选仍使用 `2db71b4`；本机新 App 不宣称与其二进制相同。

### 备份与安装审计

准确备份根目录（当前用户家目录）：
`~/Library/Application Support/墨析 OCR 工作台/maintenance-backups/2026-10-22-local-preview/`。

| 项目 | 实际核验 |
| --- | --- |
| `preflight/installed-1.2.2.app` | 旧 App 副本，3736 项文件/链接与原基线逐项相同，严格签名校验通过。 |
| `prebuild/release-candidate.app` | 构建前归档的原公开候选来源 App，10420 项清单一致、签名通过；防止构建清理覆盖。 |
| `install/previous.app` | 部署器原子移动的实际旧安装，3736 项与原基线一致；回退首选，签名有效。 |
| `independent-old.json` / `independent-candidate.json` | 替换前独立清单；即使替换后的审计写入出错也有核对依据。 |
| `install/deployment.json` / `install/installed-manifest.json` | 首次部署命令退出 0，审计存在，新旧清单与独立清单一致；该候选 10420 项在首次原生验证后仍相同、签名有效。 |
| `rollback-reader-contrast/previous.app` / `deployment.json` / `installed-manifest.json` | 首次视觉验收失败后按原 rollback 入口恢复 1.2.2；候选原子移至此处保留，审计记录实际回退。 |

旧清单文件 SHA-256：`c2f9ae299120f6ec91c0471313df897c1bb444c4ef28bcbf33876b8735c3e753`。
新清单文件 SHA-256：`c3f79fa9d92cefc4c6bd66265e889b474cbeb6774df163340fef841a01acc562`。
部署审计 SHA-256：`7a992d8865c2714c25eb7dcbc07838f26c5d400a03c209373f287f1e688ec63d`。

上述均为 App 备份和审计，不声称做了扫描数据备份或迁移。原始维护基线没有覆盖，旧备份没有删除。

### 数据保全与真实用户路径

正常退出旧版、所有服务停止后才生成稳定只读清单。磁盘全部 4 个任务为 3 completed / 1 failed，元数据可解析、32 位十六进制 ID 与目录一致；没有通过取消或重写任务取得终态。更新后、隔离测试后、正常启动后及最终退出后逐项比较均相同：

- `data/` 共 367 个文件、619490861 字节，包含原件、结果和笔记；所有文件/目录/链接清单相同。
- 旧 LM Studio 模型目录 5 个现存文件、92889 字节保持相同；这不是完整权重，不宣称模型已经可用。
- 应用管理的 `models/` 在更新前不存在，更新后仍不存在；未下载、加载、迁移或删除模型。

原生测试运行已安装的 `/Applications/墨析 OCR 工作台.app`。隔离实例、正常实例每次切换前均确认 3000/18765 空闲，旧进程退出；启动后核对监听 PID、可执行文件、工作目录和日志路径归属，再操作。

| 真实路径 | 结果与证据（仅本机忽略目录） |
| --- | --- |
| 原生版本/首页 | 1.3.0 (6)，隔离首页 0 任务；`about-1.3.0.png`、`isolated-home.png`。 |
| 系统选文件 | 打开 → 取消 → 再打开 → 选择合成 `preview-smoke.txt`，自动完成 1 页；没有使用用户历史文件。 |
| 阅读器 | 打开、内容存在及隔离任务进度保存成功，但 `isolated-reader.png` 显示深色模式白底浅字；**阅读视觉验收失败**，不能以 AX 文本存在代替可读性。未改变共享主题或识别偏好。 |
| 完整 ZIP | 原生 NSSavePanel 保存成功，页面未被下载导航中断；`native-save-dialog.png`、`after-export.png`。四条目 CRC 全通过，源 TXT 字节与输入相同，结果 TXT/MD/JSON 含完整测试标记，JSON 可解析。 |
| 模型入口 | 本机状态面板显示 Apple Silicon、MLX 固定源及下载按钮，未点击下载；`model-download-entry.png`。 |
| 来源边界 | 正常本机 Origin 为 200，外部/null Origin 和伪造 Host 为 403；`origin-guard.json`。初次 Node fetch 未实际转发 Host 覆盖值，已用本机 echo 复现测试客户端行为，再用 curl 发送真实 Host 复测；不将该测试脚本假失败当作应用缺陷。 |
| 正常目录 | 首页显示原 4 条任务，下载入口可见；只检查首页/状态面板，未打开历史阅读器或导出。摘要 `normal-ui-summary.json` 不含历史文件名。 |
| 退出 | 隔离和正常实例均通过 Cmd+Q 正常退出，前后端与相关进程退出，3000/18765 连接拒绝；两份后端日志均记录 Application shutdown complete。最终 App 保持退出，不留后台服务。 |

合成 ZIP 大小 2536 字节，SHA-256：`3433307098d8636ab0f438a1bbe0a1f7ac4d3b1813dcd76d7ad6e94367e9d939`。
私有证据目录：`test-results/local-preview-20261022/`，包含上述截图、原生/服务日志、只读清单和 `final-verification.json`；该 JSON 是首次安装后的机器检查摘要，不包含视觉通过结论。最小证据及合成 ZIP/输入另逐字节复制至耐久备份根 `evidence/`。均不提交 Git、安装包或 Release；公开文档不含历史任务名或标识。

前后端日志未检出 ERROR、Traceback、Exception 或 HTTP 5xx。原生 stderr 仍有既有诊断 `sandbox_extension_issue_file failed for : 2 (No such file or directory)` 一次；文件框与完整 ZIP 路径均成功，原因仍未证实，**不宣称日志完全无异常或此诊断已修复**。正式版仍须复查。

### Review 与剩余范围

部署前四项风险已按上述门禁执行；私有只读审计脚本独立 review 另发现 1 项 P2（ID 格式缺少后端同等正则），已修复并复核。首次证据独立 review 的 P0/P1=0，新增 P2=1：深色阅读不可读，必须撤回“阅读通过”表述。签名、数据保全、ZIP、退出和日志摘要另行回读成立。只读比较确认旧版也有相同样式，回退本身不解决该遗留问题。

首次只证实安装动作、数据保全和上述通过项，不证实整个更新完成。全量权重下载、真实图片/PDF OCR、加载后模型内存释放、Windows 目标机、公开浏览器大文件分发以及既有系统诊断仍未验收/解决；TXT 直接读取不计为 OCR。

### 按追加授权修复并重新验收

用户确认：“修复后再更新并验证”。先停止交付，已用原 `rollback` 入口、`install/previous.app` 和 `install/installed-manifest.json` 恢复旧版，审计留于全新的 `rollback-reader-contrast/`。回退后版本 1.2.2、签名有效，业务与模型清单仍完全相同；没有取消、重扫或改写历史任务。

根因：共享富文本组件继续使用工作台 `--surface` 等背景/标题色，阅读器仅继承正文 `--reader-ink`；系统深色/显式深色与工作台明亮主题组合时产生浅字白底。最小修复在 `.moxi-reader-paper` 内映射这组颜色变量到阅读器自身配色，覆盖正文、标题、表头、代码与边框，不改全局工作台、HTML 清洗、后端或存储规则。

新增 `tests/reader-theme.test.mjs` 三项源码契约/正文对比度测试；不能替代渲染验收。修复须独立 review、PR、Linux/Windows CI 与合并后再从 clean main 构建。保留原公开包和首次候选，在新的 `install-reader-fix/` 审计目录 App-only 安装；expected-current 采用回退记录的清单，不重新获取基线掩盖漂移。再次用独立合成文本/表格验证系统深色、显式深色、明亮、护眼、原始文字、完整导出及退出；只改变隔离任务的阅读主题，不改共享工作台偏好或历史任务。全部证据经后续文档 PR 回填前不登记成功。

修复提交前本机回归：57 Python、lint、`npm test`（构建 + 10 项 Node 测试）通过；旧版 3736 项与回退清单一致，保留的失败候选 10420 项与其独立清单一致。视觉修复仍待合并后原生复验。

修复代码及文档独立末轮 review P0/P1/P2=0。文档初轮两项 P2（历史部署参数可误复用、测试状态不一致）已修正并定点复核；review 代理也验证新增主题映射测试在原 CSS 上失败，能捕获该回归。原视觉缺陷仍标记为“代码修复、待实机复验”，不因 review 通过而提前关闭。
