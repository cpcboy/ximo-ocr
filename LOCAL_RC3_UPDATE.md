# 2026-10-28 本机 rc.3 候选更新

状态：准备阶段，尚未替换本机 App。用户另授权备份旧版、保留全部扫描和模型数据后更新并验证；仅本机候选试用，不发正式版或新的安装包。准确执行结果将独立 review 后经后续证据 PR 回填，不能用本方案代替已验收。

## 来源与最小改动

- 现装 1.3.0(8)，源 `cfb7c929266fe43c352ae9aadf84b021d675010b`（PR #17）；复用该批 `install-v2/installed-manifest.json` 核对漂移，不重取基线掩盖变化。
- 公开 rc.3 为 1.3.0(9)，tag/DMG源 `ee808f671712e8795c89a4d4f1c1d3f6d6287115`（PR #19）。其后到 `455d4e93fe6d2891ce9bb5a57523a9a6c3b35487` 只有6份文档变更；本批也仅改5份文档，不改模型/运行库/OCR/部署代码。
- 部署器要求干净 `HEAD == origin/main == candidate SOURCE_COMMIT`。本次文档 PR review、双平台 CI、合并及 main CI成功后，按既有流程重建同一 rc.3 应用代码，记录新实际 SHA。公开 tag、DMG、校验值和预览标识不改，本机重建 App 不宣称二进制与公开包完全相同。
- 使用 `~/cpcsoft/OCR/work/uocr2-upgrade/` 干净跟踪树；根目录用户 `.workbuddy/` 不读取、不修改、不提交。既有 worktree 的 ignored 构建、运行时、模型及审计保留。
- 微信文章正文未能安全读取；新模型名/来源未知，待用户补充，不以另一模型冒充、不开启外部推理、不绕过安全策略。

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
- 准备方案和私有审计脚本已独立对抗review，新增P0/P1/P2=0；所列三类既有退出诊断不清零。App备份、PR/CI、重建、安装及原生验收尚未完成，后续证据逐项回填，不沿用旧验收宣称通过。
