# 构建、发布与回滚

唯一仓库：https://github.com/cpcboy/ximo-ocr 。先读 `MAINTENANCE_RULES.md`；以下入口已落入源码，具体某次是否执行通过以变更执行记录和验收记录为准，不以文档命令代替验收。

用户在 2026-10-22 先确认候选分发（维护规则第 8 项），随后另明确确认备份后在本机安装候选试用（第 9 项）。仅本机试用按下方新增小节执行；正式 Release 和 Windows 安装仍不执行，完整 OCR 等正式验收门禁不因试用而变成通过。

## 发布门禁

1. 主题分支改动 → 自查 diff → 独立对抗 review（P0/P1 清零，P2 逐条处理）→ 文档 → 提交 PR。
2. Python、前端测试与 CI 通过后合并；生产只用与 `origin/main` 一致的干净 checkout。不要直接改 `/Applications` 内文件。
3. 构建前保存需要保留的旧 `.app`、EXE、DMG 及哈希，备份必须在 `build/` 外。脚本会重建 stage / `.app`，但不删除已存在的同名发行安装包，须先归档。
4. 核对没有扫描文件、OCR JSON、模型权重、日志、凭据进入 Git 或安装包。用隔离数据完成用户路径；候选构建不等同于生产。
5. Mac 全量模型首次下载及 OCR 未验证，或任何已知失败未解决时，停止正式生产部署。第 9 项仅允许本次已确认风险的本机候选试用，仍须备份、数据保全和实际验证，不得推广为常规豁免。Windows 未在目标机器验收时只允许明确标记 candidate。

## 本次候选预览版分发（不部署本机）

用户明确授权分发已经验收到候选范围的原包。本次不改应用代码、不重新打包；`v1.3.0-rc.1` 必须指向两包的实际来源 `2db71b41864cdc3ec3222279f4cf07f2a875e459`，该提交已通过 PR #2 合并和 main CI。之后的文档提交不改写包内来源，不将它们标成新构建。此安排只适用于本次原包候选分发；未来正式版仍须从最新已合并 clean main 构建及完整验收。

1. 核对工作区无无关改动、上述源已合并、后续提交只有文档；核对候选 SHA-256 与 `CANDIDATE_DELIVERY.md` 完全一致。已有包及旧版 App 备份原位保留，不覆盖。若有任何差异，停止并重新 review。
2. 将此次授权、发行说明及流程通过独立 review、PR、CI 后合并。确认远端尚无同名 tag / Release；若存在，读取其状态恢复本次流程，禁止覆盖同名资产或移动 tag。已有 lightweight/annotated tag 必须递归解析到最终 commit，并确认等于 `2db71b41864cdc3ec3222279f4cf07f2a875e459`，不符立即停止；`--target` 只影响新 tag 自动创建，不能证明已有 tag 的来源。
3. 从已合并文档创建 **draft + prerelease + latest=false**，只上传指定的两个安装器和各自 `.sha256`：

   ```sh
   gh release create v1.3.0-rc.1 \
     build/macos/output/MoxiOCR-macOS-arm64-1.3.0.dmg \
     build/macos/output/MoxiOCR-macOS-arm64-1.3.0.dmg.sha256 \
     build/windows/output/MoxiOCR-Windows-x64-1.3.0-candidate.exe \
     build/windows/output/MoxiOCR-Windows-x64-1.3.0-candidate.exe.sha256 \
     --repo cpcboy/ximo-ocr --target 2db71b41864cdc3ec3222279f4cf07f2a875e459 \
     --draft --prerelease --latest=false \
     --title '墨析 1.3.0-rc.1 · 候选预览版（未完成全量验收）' \
     --notes-file RELEASE_CANDIDATE_v1.3.0-rc.1.md
   ```

4. 核对草稿只有四个指定资产、大小及 GitHub 服务端 SHA-256 与本机相同，包源及 target 正确，说明无敏感信息。公开前再次检查远端 tag：存在则按第 2 步解析并核对最终 commit；尚不存在则确认草稿固定 target 且没有冲突 tag，公开后仍须回读验证。若上传超时，先读取草稿和资产状态；只补缺失资产，不盲目重复建 Release、不使用 `--clobber`。
5. 完整校验后用 `gh release edit v1.3.0-rc.1 --repo cpcboy/ximo-ocr --draft=false --prerelease --latest=false` 公开。复核 `prerelease=true`、`draft=false`、非 Latest、tag 解析到上述源。
6. 在真实浏览器打开发行页，检查 Pre-release 标识、限制说明、Mac/Windows 下载入口并实际点击下载；下载回读与四个资产清单的 SHA-256/大小逐一核对。保存截图及校验结果到忽略的验证目录，最终证据经后续文档 PR 回填。下载失败不能登记为验证通过。

本次无需停止正在运行的 1.2.2，也不触发模型下载；仅检查 App 文件清单未被此次分发改动。不会把扫描原件、结果、模型、日志、整个 build 或备份上传到 Release。

撤回触发：资产来源/哈希不一致、误标正式版/Latest、错误的安装或验证宣传。草稿阶段停止公开；若已公开，先编辑标题和说明醒目标记“已撤回/请勿安装”，保持 Pre-release 与非 Latest，记录原因并通过 PR 修复后另发新 rc。保留旧 tag 和原包作审计，不改写历史、不覆盖资产；不可变发行若限制操作则报告并按其允许方式标注撤回，不绕过保护。本机未更换所以无需 App 回滚。

## 本次本机候选试用（第 9 项追加授权）

详细记录见 `LOCAL_PREVIEW_UPDATE.md`。2026-10-22 首次从 PR #6 合并源 `c30850d34dc36411923360645f241c976634d082` 安装本机 1.3.0 (6)，但深色阅读视觉验收失败，已恢复 1.2.2。用户另按维护规则第 10 项授权最小配色修复，再走 review/PR/CI/合并和原生复验；未授权覆盖已公开安装包。部署器保持原样，不新增跳过来源、签名或漂移检查的参数。

**以下编号步骤是第 9 项首次尝试的历史记录，勿原样再次执行，特别是已存在的 `install/` 目录。** 第 10 项再次部署允许已 review 的 `app/globals.css` 配色和 `tests/reader-theme.test.mjs` 回归测试差异；expected-current 改用 `rollback-reader-contrast/installed-manifest.json`，backup-dir 改用全新 `install-reader-fix/`，均位于下述耐久备份根。等待 PR/main CI 成功，从该修复的合并 main 构建，构建前保留首次候选；其他签名、停服、清单、隔离验收门禁保持不变。完整参数与执行状态以 `LOCAL_PREVIEW_UPDATE.md` 末尾为准，不可把修复包标成原公开候选的相同二进制。

1. 授权与执行方案先经文档 PR、独立 review、CI、合并；从 clean main 构建，并核对 `2db71b41864cdc3ec3222279f4cf07f2a875e459..HEAD` 只包含文档差异。否则停止重新 review。
2. 核对当前 App 与维护开始清单一致；只读检查磁盘全部 `data/jobs/*/job.json`，不可只看最多 500 条的接口列表。只接受 completed/partial/failed/canceled 终态；任何其他状态、不可读取元数据或 ID 与目录名不一致都阻断更新，不能擅自取消、修复或删除。
3. 退出前确认无上传、未保存文本或待保存阅读状态，正常退出并等待保存完成；再次全量检查任务，确认 3000/18765 没有监听且旧 OCRStudio、模型及服务进程退出。此时才生成扫描、结果、笔记及两处模型目录的稳定私有哈希清单，不存在的目录也记录；不使用退出前快照掩盖或误判正常保存。清单不提交 Git、不上传。
4. 构建前归档旧构建 App。更新前单独复制现有 1.2.2 App 到可恢复目录，逐文件/链接清单与签名复核。备份使用本机应用支持目录下 `maintenance-backups/2026-10-22-local-preview/`，不在 Downloads 或 build 清理目标中；`install/` 留给部署器，必须尚不存在。旧基线清单不覆盖。
5. 运行 `npm run build`、`./mac-app/build-app.sh`，核对版本 1.3.0 build 6、真实新 main 来源、clean 构建与签名。安装前独立保存新旧 App 清单，按下方原 `install` 命令用独立候选 App、原基线、全新 `install/` 回退目录执行。不能用 rollback 模式绕过 install 的来源检查。部署器在替换后写审计，如命令异常，先回读已安装 App/previous.app 定位，不能假定未安装、盲目重试或重取基线。
6. 安装后的原生 App 先在全新隔离 `OCR_STUDIO_SUPPORT_DIR` 运行合成 TXT 的文件选择、导入、阅读、完整 ZIP 保存和退出验证；不复用旧 PID 文件。每次正常/隔离切换前，确认两端口空闲及旧进程退出；启动后核对监听 PID、命令及支持目录都属于本次实例，再做写操作。隔离实例清除继承的 `UNLIMITED_OCR_MODEL_DIR` 并设置 `OCR_STUDIO_DISABLE_LEGACY_MODEL=1`，不触发下载/加载，不修改全局 launchctl 环境。隔离 support 只隔离任务/模型/日志，默认 WebKit 主题和识别选项仍共享，不改这些偏好。随后正常启动仅检查首页、模型入口、历史任务数量；不打开历史阅读器或导出历史任务，因为这些动作可能持久化状态或准备预览。确认业务和模型文件与稳定清单逐项相同。
7. 出现启动、数据保全、导出或退出失败时停止试用，回滚前再次核对 previous.app 与原基线一致且签名有效，按原 rollback 命令恢复，不修改业务数据来掩盖失败。App-only 回滚不能恢复已被任务或阅读器改动的业务数据，前述无活动任务和隔离验证门禁不可跳过。保存真实截图及日志摘要；失败和未覆盖范围均如实回填文档 PR。GitHub Release 仍为 Pre-release/非 Latest。

## 测试命令

```sh
.venv/bin/python -m pytest -q
.venv/bin/python -m py_compile backend/*.py windows/*.py scripts/deploy_macos.py
npm ci
npm run lint
npm test
```

`npm test` 包含正式前端构建、页面/接口契约、来源摘要与打包门禁测试。GitHub Actions 在 Linux 和 Windows 跑测试，Windows 原生构建候选 EXE。`npx tsc --noEmit` 目前并非通过的门禁：仓库遗留 Cloudflare 示例缺少类型声明，见验收记录；不得把它记成通过。

## 本机候选构建

```sh
npm run build
./mac-app/build-app.sh
./windows/build-installer.sh
```

Mac 需要 Apple Silicon、Xcode/Command Line Tools、Node/npm；Windows 交叉构建另需 `/opt/homebrew/bin/makensis`。Mac 脚本下载并校验固定 Python/Node，Python wheel 按 macOS 14 解析。首次准备需要网络。

Windows 原生 PowerShell：`./windows/build-installer.ps1`，需 Node 22、Python 3.12 x64、NSIS 3.x；不绕过执行策略。`-SkipFrontendBuild` 仅接受与当前源码摘要一致的前端。

两平台入口各自生成原生 `STAGE_FILES` 通配路径，显式指定 NSIS `INPUTCHARSET UTF8`，不要改回混合分隔符或系统默认编码。`tests/test_windows_packaging.py` 使用含空格/中文的合成目录真实编译启动器与安装器；Windows CI 在安装 NSIS 后强制补跑，失败不得上传候选包。

输出：

- `build/macos/墨析 OCR 工作台.app`
- `build/windows/output/MoxiOCR-Windows-x64-1.3.0-candidate.exe` 及 `.sha256`

前端内 `BUILD_SOURCE.json` 包含 Git SHA、dirty 状态和源码摘要；打包脚本前后检查一致。`SOURCE_COMMIT` 以 `UNCOMMITTED-` 开头的候选不允许部署或公开当正式版本。

## 合并后的 Mac DMG

核对并切到已合并 main，不覆盖任何本机未提交改动；确认回退包已归档后执行：

```sh
node scripts/build_identity.mjs --require-release
./mac-app/build-installer.sh
```

DMG 入口再次检查 clean + `origin/main`，重建前端、打包、临时签名、验证 DMG，输出 `build/macos/output/MoxiOCR-macOS-arm64-1.3.0.dmg` 及 `.sha256`。
Mac 为 ad-hoc 签名，尚无 Developer ID 公证；Windows 也未做商业代码签名。不得宣称已通过 Gatekeeper、SmartScreen 或目标杀毒软件验收，不建议关闭防护或添加排除。

## 更新本机 Mac（仅 App，不动扫描数据）

先正常退出墨析，确保 3000 / 18765 无监听。保存维护开始时的已安装应用清单，并另行备份旧 App；不要在部署前重新生成清单来掩盖漂移。

```sh
.venv/bin/python scripts/deploy_macos.py snapshot /绝对路径/installed-before.json
.venv/bin/python scripts/deploy_macos.py install \
  '/绝对路径/已合并构建/墨析 OCR 工作台.app' \
  --expected-current /绝对路径/installed-before.json \
  --backup-dir /绝对路径/新的本次回退目录
```

上述 `/绝对路径/...` 是需填入实际维护记录的参数，不是可原样运行的路径。回退目录必须尚不存在，与 Applications 同一文件系统，且不在构建清理目录内。部署器检查当前 App 与维护开始清单完全一致、候选签名、Git 来源与复制哈希后原子替换；备份内生成 `previous.app`、`deployment.json`、`installed-manifest.json`。遇到漂移立即停止，不覆盖。

本次维护开始的准确清单和旧版位于本机忽略的 `.maintenance-backups/2026-10-21-model-download/`。这些是本机回退材料，不提交 Git/Release。首次基线为 1.2.2 build 5；第 9 项本机试用曾执行 install，但因视觉失败已 rollback 回该旧版。耐久回退根为 `~/Library/Application Support/墨析 OCR 工作台/maintenance-backups/2026-10-22-local-preview/`：`install/previous.app` 是原安装，`rollback-reader-contrast/previous.app` 保留失败候选；再次部署使用 `rollback-reader-contrast/installed-manifest.json` 核对当前旧版，在新的 `install-reader-fix/` 留审计。修复 App 的来源须为其真实合并 main，不能继续声称相对公开候选仅文档变化；公开资产不改。精确证据见 `LOCAL_PREVIEW_UPDATE.md`，不进行业务数据回滚或迁移。

## 真实验收和 GitHub Release

在 App 的真实 WKWebView / Windows 浏览器窗口操作：无模型首次提示 → 用户点击下载 → 暂停 → 关闭退出 → 重开续传 → 完整校验 → 选择合成图片并 OCR → 阅读/导出完整结果包 → 退出后确认模型/子进程/端口释放。校验权限、错误提示、日志。不要拿用户历史任务做测试或迁移。

Mac 本机地址 `http://127.0.0.1:3000/`；后端 `http://127.0.0.1:18765/` 的 readyz/health 仅辅助。Windows 按 `WINDOWS_TEST_REPORT_TEMPLATE.md` 记录驱动、显存、杀毒软件和安装/卸载，不能用构建通过替代。

满足门禁后，给实际合并提交创建版本 tag，通过 `gh release create` 上传对应 DMG、Windows candidate EXE、各自 SHA-256；发行说明写明源码 SHA、签名状态、实测平台、Windows 未验收项目及回滚地址。不要上传整个 build 或备份目录。发布后核对 Release 下载文件哈希和源码 tag，最终执行记录通过后续文档 PR 回填；未经验证不能标成发布成功。

## 回滚

正常退出 App，保留当前版作为第二个回退点；用部署备份的清单核对当前文件，然后：

```sh
.venv/bin/python scripts/deploy_macos.py rollback \
  /绝对路径/本次回退目录/previous.app \
  --expected-current /绝对路径/本次回退目录/installed-manifest.json \
  --backup-dir /绝对路径/新的回滚审计目录
```

不删除或覆盖应用数据/模型目录。源码用 revert PR，合并后才重新发布；发行页面说明撤回版本及有效旧版。Windows 回装保留的旧安装器，不删除 `%LOCALAPPDATA%\MoxiOCRStudio`；任何数据迁移都需另行授权，本次没有迁移。
