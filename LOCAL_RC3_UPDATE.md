# 2026-10-28 本机 rc.3 候选更新

状态（2026-10-29）：**首次原生 OCR 出现 Metal GPU Timeout，P1 未关闭，本机安装暂停。**独立备份、重建与包核验已完成，同参数新进程复测成功仅说明未复现；本机仍 build8，从未被替换。用户另授权备份旧版、保留全部扫描和模型数据后更新并验证；仅本机候选试用，不发正式版或新的安装包。下方计划不是已完成安装证明，实际证据见末节。

## 来源与最小改动

- 现装 1.3.0(8)，源 `cfb7c929266fe43c352ae9aadf84b021d675010b`（PR #17）；复用该批 `install-v2/installed-manifest.json` 核对漂移，不重取基线掩盖变化。
- 公开 rc.3 为 1.3.0(9)，tag/DMG源 `ee808f671712e8795c89a4d4f1c1d3f6d6287115`（PR #19）。其后到 `455d4e93fe6d2891ce9bb5a57523a9a6c3b35487` 只有6份文档变更；本批也仅改5份文档，不改模型/运行库/OCR/部署代码。
- 部署器要求干净 `HEAD == origin/main == candidate SOURCE_COMMIT`。本次文档 PR review、双平台 CI、合并及 main CI成功后，按既有流程重建同一 rc.3 应用代码，记录新实际 SHA。公开 tag、DMG、校验值和预览标识不改，本机重建 App 不宣称二进制与公开包完全相同。
- 使用 `~/cpcsoft/OCR/work/uocr2-upgrade/` 干净跟踪树；根目录用户 `.workbuddy/` 不读取、不修改、不提交。既有 worktree 的 ignored 构建、运行时、模型及审计保留。
- 原微信链接未能安全读取；用户后提供 PDF，已核对为 MiniCPM-OCR 1.0 和 Jev。两款一起接入及 Mac 本机非量化隔离验证已获确认；低分最多追加 3 次自动识别，具体阈值及结束决策仍需确定。新增接入另走一轮实现/review/PR/CI/合并和验收，不更换默认引擎，不绕过当前安装阻断。

## 门禁与操作

1. 检查 App/前后端进程与 3000/18765。现时未运行只是一次观察；每次启动/安装前重查。若用户重开，先确认保存并正常退出，不强杀。
2. 只读遍历正式 `data/jobs`：每个目录必须有可解析元数据，ID为32位小写十六进制且等于目录名，状态只能 completed/partial/failed/canceled；数量取实际检查，不沿用旧4任务假设。阻止启动自动恢复未结束任务。只输出数量/状态摘要，不泄露历史文件名或配置。
3. 新建私有审计根 `~/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/`（0700）。以旧安装清单检查App漂移和签名，保存 `installed-before.json`。对 `~/Library/Application Support/墨析 OCR 工作台/data/`、其 `models/Unlimited-OCR-MLX/`、`models/Unlimited-OCR-2-bf16/` 及 `~/.lmstudio/models/LoJexLLM/Unlimited-OCR-MLX/` 建内容/类型/权限清单；不复制 API 密钥、不改业务数据。此为保全核对，不冒称扫描数据备份。
4. 构建前把 worktree 内旧 build9 App 原样归档到新审计根 `prebuild/rc3-published.app`，先核对上一批清单/签名，记持久化日志、原子移动、回读复核。另 `ditto` 当前安装 App 到 `preflight/build8.app`，核对清单/签名；这与随后安装器的 `previous.app` 是两层旧 App 回退点，均不得覆盖。
5. 本机运行既有 `build/validation-venv/bin/python -m pytest -q`、`npm run lint`、`npm test`。合并后执行 `npm run build`、`./mac-app/build-app.sh`，不执行 build-installer。核对真实源码、前端来源、严格签名、固定依赖/适配许可；包内不得有模型、扫描/笔记/接口配置、日志、测试环境或凭据。运行库应与归档已验收 rc.3 完全相同，不自动升级依赖。
6. 先运行候选：全新独立 `OCR_STUDIO_SUPPORT_DIR`/`OCR_STUDIO_DATA_DIR`，模型显式指向已校验隔离2.0目录，不使用用户远程接口或复制配置，不改全局环境。真实原生文件框选合成3页PDF、阅读深色表格、系统保存完整ZIP，检查原始输出/页数/完整性。正常退出，核对卸载、日志、端口及相关进程。
7. 安装前再次核对全部受保护清单/任务终态/旧App、候选签名与清单、clean main。运行下方原 install 入口，新 `install-rc3` 必须不存在；异常先核对实际App/备份/审计状态，不盲目重试或重取基线。
8. 已安装App在另一全新独立目录运行，使用原位正式2.0模型（只读，不下载/修复），真实系统文件框选120行合成图片、MLX识别、阅读搜索、保存完整ZIP和退出。核对120条数字差异均保留，raw/reader/text完整、模型自动卸载、来源403边界、前后端无Traceback/ERROR/5xx。
9. 再核对历史任务终态后正常启动安装版，仅看首页数量/模型状态，不打开历史阅读器、不改共享主题偏好、不发起用户任务或导出。正常退出，全量复查4处受保护目录的内容/类型/权限、App和旧备份清单/签名、全部服务退出。保留已知信号量清理、sandbox、IMK诊断及未公证/全新Mac未验边界。

## 原部署与回退命令

以下路径为本批独立参数；仅在上述门禁满足、目标审计子目录尚不存在时执行，不是可重复安装脚本。Python为该worktree已验证的3.11解释器。

```sh
cd /Users/chenpengcheng/cpcsoft/OCR/work/uocr2-upgrade
build/validation-venv/bin/python scripts/deploy_macos.py install \
  '/Users/chenpengcheng/cpcsoft/OCR/work/uocr2-upgrade/build/macos/墨析 OCR 工作台.app' \
  --expected-current /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/installed-before.json \
  --backup-dir /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/install-rc3
```

部署器保留 `install-rc3/previous.app`（实际旧build8）、`deployment.json` 和 `installed-manifest.json`；安装前已有独立候选清单，避免后写审计失败时失去核对依据。不得直接覆盖 `/Applications` 或修改来源文件。

失败时正常退出候选、确认端口已停、备份/当前清单一致后，用原 rollback 入口；新 `rollback-rc3` 必须不存在：

```sh
cd /Users/chenpengcheng/cpcsoft/OCR/work/uocr2-upgrade
build/validation-venv/bin/python scripts/deploy_macos.py rollback \
  '/Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/install-rc3/previous.app' \
  --expected-current /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/install-rc3/installed-manifest.json \
  --backup-dir /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-28-local-rc3/rollback-rc3
```

只回退App，不覆盖任何扫描/模型/接口配置。回退后真实启动旧版并复查保全清单；源码文档变更通过revert/修正PR，不强推、不改旧tag/资产。若App或数据漂移，先停止查清，不用旧业务数据覆盖新写入。

## 证据与交付

准备/安装/最终证据分别独立 review，P0/P1清零；任何关键路径失败不登记完成。私有目录留输入/合成ZIP、截图、版本与源码、App/数据/模型清单、日志摘要、部署回执；不入Git或安装包。合成临时support退出后可恢复归档到审计目录，不清理保护路径或旧备份。公开文档只给摘要/哈希、CI/PR链接和验证边界。

2026-10-29 继续执行：现装仍 build8，3000/18765 无监听；独立 4173 离线阅读器不属于本次更新，不终止。当前磁盘实际可用约85 GiB。

- 前次回归曾有172通过/6失败，后续遭遇ENOSPC；保留为历史失败，未据此安装或跳过门禁。本轮未修改代码，重新运行同一验证环境得到 **178 Python通过（6条弃用告警）**、lint通过、正式前端构建及 **12 Node测试通过**。复跑通过不等于已证实前次全部失败的根因。
- 准备方案和私有审计脚本已独立对抗review，新增P0/P1/P2=0；所列三类既有退出诊断不清零。后续执行如下，不沿用旧验收宣称本次通过。

## 2026-10-29 实际执行与阻断

### 已完成的准备与备份

- 准备提交 `ba12f5eeb4f3bc4a5ce22f1df3cd3ce05dc51675`，PR [#21](https://github.com/cpcboy/ximo-ocr/pull/21) 于 10:38:12Z 合并，实际候选源 `0b691375c439db1c1f0ce4b940a658221c16d983`。PR CI [40858431523](https://github.com/cpcboy/ximo-ocr/actions/runs/40858431523)、main CI [40859127611](https://github.com/cpcboy/ximo-ocr/actions/runs/40859127611) 的 Linux/Windows 均成功。
- 审计根 `.maintenance-backups/2026-10-28-local-rc3/` 已建为私有目录。`preflight/build8.app` 独立复制旧安装版，`prebuild/rc3-published.app` 原子归档旧构建；二者清单和严格签名通过，旧构建另与只读挂载公开 DMG 比对。公开 DMG、tag、Release 没有修改。
- 从 clean main 执行原 `mac-app/build-app.sh` 重建 build9。20602 项清单、前端来源、后端 Git 内容、严格 ad-hoc 签名通过；运行库与已归档 rc.3 完全一致，未新增权重、用户数据或凭据。候选前端摘要 `117c18693e0900cd84911bf6c3c3976bb58b7866f2a08a1807fb32e53a34de7a`。尚无 Developer ID 公证。

### 首次失败与一次有界复测

| 项目 | 首次候选 | 新进程复测 |
| --- | --- | --- |
| 独立 support | `work/local-rc3/native-candidate` | `work/local-rc3/native-retest` |
| 合成任务 | `4ba765f8fada422396c59bd8ec77116c` | `91eeaee29d7a43bd87380200f8f7a2df` |
| 原生系统选文件 | 同一合成三页 PDF | 同一 PDF |
| OCR | 第1页17.34秒后 GPU Timeout，后2页完成，任务 partial | 3页 completed，第一页12.2秒 |
| 真实路径 | 失败界面/错误现场保留，没有记为通过 | 阅读第三页表格、系统保存完整ZIP、自动卸载、正常退出通过 |
| 判定 | 新增 P1，停止安装 | 仅未复现；P1和安装阻断仍保留 |

两次输入 SHA-256 均为 `b6432bb9daa04226e3dbe224a80fd97455d5c06151aec8da995e758cf67ecb99`。options 完全相同：precision、160 DPI、max_length 8192、默认 prompt；使用同一已校验 BF16 权重、候选源和运行库，没有降低精度、分辨率、上下文或关闭系统保护来求通过。

首次异常定位至 `MLX2Engine.scan → stream_generate → generate_step → mx.async_eval`：`[METAL] Command buffer execution failed: Caused GPU Timeout Error (00000002:kIOGPUCommandBufferCallbackErrorTimeout)`。两页随后成功不能抵消第一页失败。只读 OS GPU 日志查询未返回进一步证据；观察到其他系统进程负载，但没有因果证据，不将其断言为根因，也未终止其他程序。独立 review 确认这是 OCR 关键路径 P1，不是上传或导出故障。

复测 ZIP 为 `evidence/retest-complete.zip`，284296 字节，SHA-256 `21772a44975a269e4a28576d0b7217796969315df9df89f6ec7da42b767cf537`。CRC、全部成员、源文件字节、3页预览、JSON/MD/TXT与当前合成任务一致，页码唯一有序、各页标记/raw/text完整、无截断。复测后台无 Traceback/ERROR/5xx，仍有既有信号量和 sandbox 退出诊断；不声称零告警。该次不是完整安装版验收，未执行120条安装后测试或正常数据启动。

### 保全结果、证据与后续门禁

- 11:05:44Z 完整复查：已装 App 仍为 build8 / `cfb7c929266fe43c352ae9aadf84b021d675010b`，20602项及签名未变；候选与两份旧App备份未漂移。
- 历史11任务仍为9 completed、1 canceled、1 failed。`data`502、managed1.0模型14、LM Studio1.0模型7、managed2.0模型13项的内容/类型/权限与本次基线一致。未复制接口密钥、未打开旧阅读器、未重新下载或更换生产模型。
- 两次均正常退出；3000/18765及相应后端进程已停止。4173独立离线阅读器未干预。`install-rc3`不存在，部署未发生，无需回滚；旧App独立备份保留供后续使用。
- 私有审计证据：`preflight.json`、`candidate-verification.json`、`before-candidate.json`、`retest-native-verification.json`、`after-retest.json`、两次console日志及两隔离support的日志/任务。截图 `evidence/candidate-gpu-timeout.png`、`evidence/retest-three-pages.png`。这些文件不提交 Git 或安装包。
- 独立 review 修正了验包/ZIP绑定的4项P2，后续脚本复核无新增问题；实际 OCR 超时 **P1=1 未关闭**。文档回填不放行部署。后续须定位或通过明确、经审查的修复重新执行真实关键路径；不能凭单次复测成功或 CI 成功直接安装。
- 此后 main若有新提交，当前候选不再满足 `SOURCE_COMMIT == HEAD == origin/main`。继续安装前必须归档当前候选、从最新干净合并源重建并复验，不改写SOURCE_COMMIT、不用rollback方式安装新版本。原有回滚命令只在真正执行新安装后使用，不能对尚不存在的 `install-rc3` 运行。
