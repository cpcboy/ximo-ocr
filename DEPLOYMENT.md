# 构建、发布与回滚

## 2026-10-28 本机 rc.3 更新（当前批次）

用户明确授权备份旧版、保留全部数据/模型后更新本机。沿用下面原部署器的 clean main、来源、签名、漂移与回退门禁，不复用历史安装目录；完整步骤、实际阶段与精确回退参数见 [LOCAL_RC3_UPDATE.md](LOCAL_RC3_UPDATE.md)。当前仅准备，尚未安装。不改应用代码/运行库/模型，不生成或覆盖公开安装包，不操作 Windows。文章新模型接入另待准确名称和官方来源。

## 2026-10-27 rc.3：仅 Mac 2.0 候选分发（本批次）

用户确认仅发布Mac 2.0候选安装包，非正式、非Latest，不再次更新本机或操作Windows。只改Mac打包标识、版本测试及发布文档，不改OCR逻辑、模型清单或权限。状态见 [RC3_VALIDATION.md](RC3_VALIDATION.md)，对外说明见 [rc.3候选说明](RELEASE_CANDIDATE_v1.3.0-rc.3.md)。

**本批次已执行并公开** [v1.3.0-rc.3](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.3)，2026-10-27T18:56:47Z；包源/tag为PR #19合并`ee808f671712e8795c89a4d4f1c1d3f6d6287115`。PR/main CI、新DMG隔离原生路径、真实内置浏览器两附件下载及独立公开回读已通过；两资产校验值与原包相同，Latest端点404，未设正式版。现装1.3.0(8)/cfb7c929未替换或重启，扫描及新旧模型保全；三类非阻断退出诊断如实保留。以下命令是已执行流程，**不能再次创建/覆盖现存rc.3、旧包或审计目录**。后续文档合并不重新构建此DMG。

1. 在独立worktree完成自查、独立review、文档、PR和双平台CI；合并后等main CI成功，核对clean `HEAD == origin/main`。Mac App为1.3.0(9)，Windows仍rc.2；CI的Windows测试artifact不作为本次发行。
2. 构建前将该worktree旧build8 App保全到新的`~/cpcsoft/OCR/.maintenance-backups/2026-10-27-rc3/prebuild/`，逐项核对来源、清单和签名。现安装版/受保护数据及三处模型目录建立只读内容/类型/权限清单；复核当前安装与上一批清单无漂移。旧公开包不受新worktree构建影响，不移动/覆盖。
3. 执行既有`./mac-app/build-installer.sh`，只生成`build/macos/output/MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg`及`.sha256`。同名存在就停止，不删文件重新打包。核对DMG、签名、真实`SOURCE_COMMIT`、前端来源、固定运行时和许可；排除模型权重、用户数据、凭据、日志、测试环境。
4. 只读挂载新DMG，正常隔离运行其中App，使用全新support/data目录和既有已校验隔离2.0模型，不改全局环境；无模型提示、系统选文件、合成图片/PDF OCR、阅读、系统保存ZIP和退出须真实验证。3000/18765须空闲；若用户App运行，停止并先确认正常退出，不强占端口。保留两项既有非阻断诊断，本批次另记录IMK退出消息通道诊断，共三类，不屏蔽或记为已修复；新增关键路径失败即不发布。退出后核对安装版/数据/模型不变，卸载DMG。
5. 新包/证据/发行正文独立review后，确认无同名远端tag或Release；若存在先读取恢复流程，不重复创建或覆盖。用`gh release create v1.3.0-rc.3 <DMG绝对路径> <SHA256绝对路径> --repo cpcboy/ximo-ocr --target <实际合并包源完整SHA> --draft --prerelease --latest=false --notes-file <已核验正文>`建草稿。尖括号必须换成实测值，不可原样执行。正文附真实包源、两资产大小/哈希与未验边界，文档链接用GitHub完整URL。
6. 草稿仅上述两资产，服务端digest/size与本机一致，tag（如已生成）须解析到真实包源；确认后`gh release edit v1.3.0-rc.3 --repo cpcboy/ximo-ocr --draft=false --prerelease --latest=false`。不移动旧tag、不使用clobber、不上传Windows包。
7. 发布后真实浏览器看Pre-release/限制说明并点击DMG和校验文件下载，独立公开回读同一资产，核对字节数/SHA-256/tag/非Latest。任何浏览器/系统拦截不绕过、不登记通过。实际证据经独立review和后续文档PR回填，不把后续文档SHA冒充包源。

回退：草稿验证失败则保持不公开。已公开后若来源、哈希、关键路径或发布标识错误，先醒目标记撤回/请勿安装，保留候选/非Latest及原tag/包作审计，修复走新PR和新候选，不覆盖历史。只做分发，**本批次无需回滚或重装本机App**；旧rc.2仍保留，但它不含2.0，不能把退回rc.2说成保留2.0。已有本机build8回退方案仍见下节，不因发布自动执行。

## 2026-10-27 Unlimited-OCR 2.0 本机升级（本批次）

用户批准 BF16 隔离测试通过后更新本机，允许正常退出，并确认数字安全去重口径。只构建/安装 Mac App 1.3.0(8)，**不调用安装器/Release 发布入口、不安装 Windows**。来源、阶段状态和证据见 [UNLIMITED_OCR2_VALIDATION.md](UNLIMITED_OCR2_VALIDATION.md)。本批次已从 PR #17 合并 `cfb7c929266fe43c352ae9aadf84b021d675010b` 完成构建、候选原生验收、备份安装及安装后复验；PR/main CI均成功。下列步骤保留执行口径，**`install-v2/`已存在，不得重复执行该安装命令**。

1. 主题分支完成代码/文档独立 review、178项本机 Python（含 Mac 数值门禁）、lint、构建及 Node；PR 与 main CI 成功后，从干净的 `HEAD == origin/main` 构建。非 Mac CI 跳过 MLX 数值测试不能替代 Mac 实测。
2. 用户已保存并正常退出；核对4个历史任务终态、3000/18765端口空闲。当前旧 App 来源 afc73d5685192193fddf9e843f4034a35487c55d，先与上次安装清单核对，不重取基线掩盖漂移。本次私有审计根为 `~/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/`，保存 `installed-before.json` 与 `data-model-before.json`（扫描/结果/笔记/接口设置、managed 1.0 与 LM Studio 1.0的内容及权限）。
3. 在独立 worktree 构建 `npm run build`、`./mac-app/build-app.sh`。当前该 worktree 没有旧 `.app`；如后续重建需保留首次候选并校验再重建。验证签名/来源/完整运行时，不把模型或测试数据放入包。运行候选时设置全新 `OCR_STUDIO_SUPPORT_DIR`、`OCR_STUDIO_DATA_DIR` 及指向隔离已校验 2.0 的 `UNLIMITED_OCR_MODEL_DIR`，不修改全局环境。真实原生选文件、OCR、阅读、ZIP保存、正常退出须通过。
4. 仅向尚不存在的正式 `models/Unlimited-OCR-2-bf16/` 添加固定清单的11文件；排除缓存/临时分片/模型Python，逐个大小和SHA-256校验，写完整收据。保留两处旧1.0，不覆盖任何现存模型目录。如目标存在先停止核对，不强行合并目录。
5. 端口空闲且候选与合并源一致后，用既有入口执行（路径按实际 worktree 解析为绝对路径）：

   ```sh
   build/validation-venv/bin/python scripts/deploy_macos.py install \
     "$PWD/build/macos/墨析 OCR 工作台.app" \
     --expected-current /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/installed-before.json \
     --backup-dir /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/install-v2
   ```

   上述Python路径相对于本次独立worktree `~/cpcsoft/OCR/work/uocr2-upgrade/`；其他checkout须使用实际已验证的Python 3.11解释器。执行时`install-v2`必须不存在。现已生成旧App备份`install-v2/previous.app`、`deployment.json`和`installed-manifest.json`，禁止手改App或绕过clean main/漂移/签名门禁。
6. 安装后的真实原生合成用户路径仍在全新隔离数据目录进行；正常数据启动只读首页/模型信息/4条历史任务数量，不打开历史阅读器。正常退出后逐文件核对原389个data条目、14个managed 1.0条目、7个LM Studio条目的内容/类型/权限不变（含目录，不等同文件数）；核对模型卸载、服务退出、日志无新增错误。实际部署/证据另经文档PR回填，不把后续文档SHA冒充App来源。

实际结果：候选系统文件框选3页PDF、深色表格阅读、系统保存ZIP通过；安装版用正式新模型目录扫描120条小字，5349字/57.5秒、阅读搜索和完整ZIP通过，任务后自动卸载。普通启动只读确认原4条历史任务及新模型就绪。退出后数据/两处1.0模型389/14/7条目内容、类型与权限全相同；新App20602项、旧备份10424项清单与签名均通过，新模型11文件全量哈希/收据通过。3000/18765关闭、相关进程退出。保留1 semaphore清理告警及原生sandbox诊断两项非阻断P2，不宣称根因解决；详见验证记录。

失败回退：正常退出并确认端口空闲，用原 `scripts/deploy_macos.py rollback`，candidate 为上述 `install-v2/previous.app`，expected-current 为 `install-v2/installed-manifest.json`，backup-dir 为**新的** `rollback-v2/`；部署器先保护失败候选，再恢复旧App。本次尚未回退，确认该新目录不存在后，命令为：

```sh
cd /Users/chenpengcheng/cpcsoft/OCR/work/uocr2-upgrade
build/validation-venv/bin/python scripts/deploy_macos.py rollback \
  '/Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/install-v2/previous.app' \
  --expected-current /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/install-v2/installed-manifest.json \
  --backup-dir /Users/chenpengcheng/cpcsoft/OCR/.maintenance-backups/2026-10-27-uocr2/rollback-v2
```

只回退应用，旧模型仍在原位置，不覆盖任何业务数据；新2.0权重可保留供排查，不自动删除。源码另走revert PR，不强推main。后续证据文档PR不重新构建或安装App，不把其SHA冒充实际App源`cfb7c929...`。

## 2026-10-23 本机源码工作区迁移

用户指定迁至 `~/cpcsoft/OCR`。按 [PATH_MIGRATION.md](PATH_MIGRATION.md) 先 PR/review/CI/合并，再做同卷原样迁移、8 个 venv 路径修复和隔离浏览器验收。新目录为后续开发/构建起点，源码脚本仍自动推导根目录。
保存全树清单、环境原文件和旧 dist；不重写历史安装包/签名/审计，不迁移安装版扫描及模型，不重启或更新 App、不发布新候选。既有 CI 测试 artifact 不是发行。迁移失败按该文档移回旧根；业务数据不回滚。

实际迁移已在 PR #13 合并源 `6cb53be3b00fe9c517a23107e7b2ebd1d29e2e53` 完成；新根与源树全量核对通过，旧根不存在。开发环境已重定位，源码网页真实导入/阅读/完整包导出通过且临时服务已停止；不等于安装版更新。私有回退/审计在 `~/cpcsoft/.ocr-migration-20261023/`，包含 8 文件原件、全树清单和旧 `dist-before/`，不能清理为普通缓存；详细证据和仍保留的历史路径例外见 PATH_MIGRATION 的实际验收章节。

## 2026-10-23 源码交接（不是应用部署）

用户本次仅要求详细 DeepSeek 交接工单与源码包。入口见 [START_HERE-DEEPSEEK.md](START_HERE-DEEPSEEK.md)。
应用功能基线为 PR #11 合并 `352665be7f147474af1cf93f522958e3972cb052`；本次文档 PR 成功 CI/合并后，
从干净 main 的 Git 跟踪树导出 ZIP（`git archive --format=zip --prefix=<单一包根目录>/ --output=<全新ZIP路径> HEAD`）。
尖括号为需核对的实际参数，目标 ZIP 必须不存在；不递归压缩工作目录、不包含 `.git`、ignored/untracked 或业务数据。
交付时单独给 SHA-256、精确源 SHA；解压到全新临时目录，核对 CRC、所有文件与 Git blob 一致、中文名、链接和入口可读。
文档 PR 和打包后的验证结果分别留证；真实阅读入口验证不冒充新 OCR/原生 App 验收。

本次不手工构建/交付/发布新安装器，不运行 install，不触发模型下载，不替换、退出或重启用户 App，不新建/改动 GitHub Release。
保留既有 PR/main CI 的 Windows 测试安装器构建及 7 天 artifact；这不属于新候选发行或实机验收，也不进入交接包。
历史单次安装/分发授权不转移给新维护者；新的 MLX 原生更新仍需逐次确认和下方原部署门禁。
交接 ZIP 没有 Git 历史，不能直接通过来源门禁；开发者应 clone 官方仓库，不伪造 SOURCE_COMMIT 或删掉校验。
文档错误通过 revert/修正文档 PR，重导出不同文件名的交接包；不覆盖历史交付，无应用回滚需求。

## 当前 MLX 效率优化（未部署）

本次用户要求研究并优化 Mac 无损推理效率。按既有 review/PR/CI/合并流程，验证只用隔离合成图及已校验模型；公开 rc.2、安装版和用户数据不变。替换本机 App 的追加确认尚待答复，未确认不执行 install、不发布新的公开安装包。基准命令/来源/质量与性能边界见 MLX_PERFORMANCE.md。

获确认后仍须使用下方原 snapshot/install/rollback 入口，新建本次审计目录，先保存旧构建、核对安装漂移/任务终态、保全扫描和模型，再从 clean main 构建并验收；不得复用历史 install 目录或覆盖发行资产。无数据库/业务数据迁移。任一真实路径失败停止并 App-only 回退。

唯一仓库：https://github.com/cpcboy/ximo-ocr 。先读 `MAINTENANCE_RULES.md`；以下入口已落入源码，具体某次是否执行通过以变更执行记录和验收记录为准，不以文档命令代替验收。

用户在 2026-10-22 先确认候选分发（维护规则第 8 项），随后另明确确认备份后在本机安装候选试用（第 9 项）。仅本机试用按下方新增小节执行；正式 Release 和 Windows 安装仍不执行，完整 OCR 等正式验收门禁不因试用而变成通过。

## rc.2 新候选分发（第 11 项，当前流程）

本次只重建/分发两平台候选，不替换已安装 App、不操作 Windows。以下 rc.1 和本机试用章节保留历史，不复用其 tag/SHA/资产名。

2026-10-22 已按本流程公开 [v1.3.0-rc.2](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.2)，实际包源/tag `3e9a7e2ea2bc33fd58cafd33520a1928599a28c3`。下列命令是流程说明，不能再次创建或覆盖本批次资产；执行证据、未验范围及私有备份位置见 RC2_VALIDATION.md。用户已另确认正常退出当前 App 后隔离测试，不替换现安装版；实际已正常退出并完成新 DMG 原生路径。

1. 版本/文档经独立 review、PR、CI、合并；main CI completed/success 后核对 clean HEAD == origin/main。旧产物已在应用支持目录 `maintenance-backups/2026-10-22-rc2/prebuild/` 归档，核对回读哈希；不要覆盖 rc.1。
2. 执行 `./mac-app/build-installer.sh`（会先构建网页）及 `./windows/build-installer.sh`；输出为 `MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg` / `MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe` 及同名 SHA-256。Mac 内版本 1.3.0(7)，Windows 数值 1.3.0.2；仅候选，不改签名或来源门禁。
3. 核对两包实际 SOURCE_COMMIT 相同且等于此 main；只读挂载 DMG、严格签名、解包 EXE、检查前端阅读修复/许可与排除扫描/模型/日志/密钥。正常退出用户 App 必须先确认保存，隔离目录做原生阅读/导入/ZIP/退出，不能连接生产服务代替。
4. 将真实源 SHA/资产哈希/签名与未验收边界补到基于已合并 `RELEASE_CANDIDATE_v1.3.0-rc.2.md` 的发行正文；未知同名远端 Release/tag 立即停止核对。tag 不存在时用 `gh release create v1.3.0-rc.2 <四个明确资产路径> --repo cpcboy/ximo-ocr --target <已核对包源完整SHA> --draft --prerelease --latest=false --notes-file <已复核正文>`。尖括号为必填实际值，不可照抄执行。
5. 草稿四资产服务端 digest/size 逐一与本地核对。已有 tag 必须递归解析到实际包源，不只检查 targetCommitish。来源/状态/正文/文件完整后执行 `gh release edit v1.3.0-rc.2 --repo cpcboy/ximo-ocr --draft=false --prerelease --latest=false`；不使用 clobber，不移动旧 tag。
6. 真实浏览器查看 Pre-release、限制说明、实际点击两平台安装器与校验文件；记录浏览器下载是否完成、拦截与截图，独立公开回读哈希。浏览器受阻不能记通过或绕过；候选实际状态经独立 review/证据 PR 回填 RC2_VALIDATION 与维护表。

撤回条件及做法沿用下方候选流程：来源/哈希错误、误标正式/Latest、关键路径失败时停止公开或标记撤回，保留 tag/原包，再走修复 PR。未更换本机 App，无需本机回滚；扫描/模型不触碰。

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

详细记录见 `LOCAL_PREVIEW_UPDATE.md`。2026-10-22 首次从 PR #6 合并源 `c30850d34dc36411923360645f241c976634d082` 安装本机 1.3.0 (6)，因深色阅读视觉失败恢复 1.2.2。用户第 10 项授权的最小修复随后经 review / PR #7 / CI / 合并，从 `b7d29292c18aa30fa00e4aef9f33ca57663100ad` 构建，已备份更新实际 App 并复验四主题/文件框/合成导入/完整 ZIP/退出及数据保全。当前 1.3.0(6) 候选，实际回退点为 `install-reader-fix/previous.app`；未覆盖公开安装包。部署器保持原样，不新增跳过来源、签名或漂移检查的参数。

**以下编号步骤是第 9 项首次尝试的历史记录，勿原样再次执行，特别是已存在的 `install/` 目录。** 第 10 项再次部署已 review 的 `app/globals.css` 配色和 `tests/reader-theme.test.mjs` 回归测试差异；当时 expected-current 为 `rollback-reader-contrast/installed-manifest.json`，backup-dir 为 `install-reader-fix/`。这次安装也已执行，**`install-reader-fix/` 已存在，不得复用这些 install 参数**。未来更新须另立记录、核对现有安装清单、新建独立审计目录，等待新 PR/main CI 成功并保留旧构建；签名、停服、清单、隔离验收门禁不变。当前回退参数和证据见 `LOCAL_PREVIEW_UPDATE.md` 末尾，不可把修复包标成原公开候选的相同二进制。

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
- `build/windows/output/MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe` 及 `.sha256`（当前候选，已存在的文件禁止覆盖）

前端内 `BUILD_SOURCE.json` 包含 Git SHA、dirty 状态和源码摘要；打包脚本前后检查一致。`SOURCE_COMMIT` 以 `UNCOMMITTED-` 开头的候选不允许部署或公开当正式版本。

## 合并后的 Mac DMG

核对并切到已合并 main，不覆盖任何本机未提交改动；确认回退包已归档后执行：

```sh
node scripts/build_identity.mjs --require-release
./mac-app/build-installer.sh
```

DMG 入口再次检查 clean + `origin/main`，重建前端、打包、临时签名、验证 DMG，当前源码输出 `build/macos/output/MoxiOCR-macOS-arm64-1.3.0-rc.3.dmg` 及 `.sha256`；本批次是否已生成以RC3_VALIDATION为准，同名存在禁止覆盖。rc.1/rc.2文件名仅用于历史批次，不重新生成旧发行名。
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

本次维护开始的准确清单和旧版位于本机忽略的 `.maintenance-backups/2026-10-21-model-download/`，不提交 Git/Release。首次基线为 1.2.2 build 5；第 9 项候选视觉失败后已 rollback。第 10 项修复部署现已完成：耐久根 `~/Library/Application Support/墨析 OCR 工作台/maintenance-backups/2026-10-22-local-preview/` 下，`install-reader-fix/previous.app` 保留当前可回退旧版，`install-reader-fix/installed-manifest.json` 对应现装修复版；`rollback-reader-contrast/previous.app` 是首次失败候选，只作历史审计，不能拿它代替旧版回退点。修复版来源固定为实际合并构建源 `b7d29292`，证据文档合并不修改包内 SHA；公开资产不改。精确证据和可执行 rollback 参数见 `LOCAL_PREVIEW_UPDATE.md`，不进行业务数据回滚或迁移。

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
