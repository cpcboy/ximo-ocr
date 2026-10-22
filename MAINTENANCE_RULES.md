# 墨析 OCR 工作台维护铁律

状态：用户已确认下方八项项目口径。维护规范正式启用；仅完成文档不代表功能、安装包或实机验收完成。2026-10-22 用户追加授权候选预览版分发；1.3.0 仍非正式版，全量模型 OCR 未验收前不更新生产。

## 用户原文

【第一步：写入文档（只做一次）】
1. 先检查项目根目录现有的 AI 指令文件：AGENTS.md、CLAUDE.md、.cursor/rules、.github/copilot-instructions.md、CONTRIBUTING.md、README.md。
2. 新建 MAINTENANCE_RULES.md，把本提示词中的《维护铁律》原文写入；不要覆盖现有文档。
3. 在项目现有的 AI 指令文件里加一条强制引用（优先用已有的；都没有就建 AGENTS.md）：
“任何代码、配置、数据变更，必须先读 MAINTENANCE_RULES.md，并按其中六步执行；未完成六步不得声称完成。”
4. 在 MAINTENANCE_RULES.md 中补齐本项目信息：测试命令、构建命令、部署命令、线上验证地址、文档路径、回滚方式。不知道的先问我，不要编造。
5. 在 MAINTENANCE_RULES.md 末尾建一张《变更执行记录》表：
日期 | 变更内容 | review 结论 | 文档更新 | commit | 部署 | 验证证据 | 回滚方式
6. 这次文档创建单独提交，commit message 用：“docs: 建立维护铁律与执行规范”。

【之后每次任务开始时】
- 先读 MAINTENANCE_RULES.md 和项目 AI 指令文件；
- 用一句话复述本次要走的六步、涉及的风险点和验证方式；
- 然后再开始改代码。没有读文档、没有复述，不许动手。

【维护铁律六步，顺序不可变】
1. 改代码：先复述需求和已确认的口径；先读现有代码、文档和配置，给出最小改动方案。需求有歧义，或涉及权限、流程、数据口径时，先问我，不要猜。
2. Review：改完先自查 diff，再让另一个 review 代理/同事做对抗 review；按 P0/P1/P2 列出问题并逐条修复。P0/P1 未清零，不许进入下一步。
3. 写文档：更新 README/CHANGELOG/部署文档，写清改了什么、为什么、影响面、回滚方式。文档、git、线上必须三者一致。
4. 提交 git：只提交本次相关文件；提交信息写清模块和目的；不提交密钥、临时文件、生产数据。
5. 部署：先备份/留回退点；核对线上没有被人绕过 git 改过；按项目规定的方式部署；数据库变更必须先停写、备份、迁移、校验，再启动。
6. 真实验证：必须用真实浏览器/真实用户路径操作验证，不能只看接口 200 或健康检查；检查权限、边界、日志无报错；把验证证据（页面/截图/状态码/日志）发给我。验证失败就回到第 1 步，不许带病上线。

【三条底线】
A. 不直接操作生产业务数据。必须改时：先拿到明确授权 → 备份 → 用官方入口或可审计脚本 → 写审计日志 → 可回滚。禁止“先改了再说”。
B. 不擅自放宽权限、流程或防呆规则。涉及角色、审批、锁定、拦截的变更，必须先给方案让我确认；确认后再改。
C. 所有业务数据只存数据库/对象存储，不落本地文件；本地只放代码和临时验证产物，验证完清理。

【每次交付必须给我】
- 改了哪些文件、为什么；
- review 发现的问题和修复情况；
- 文档更新位置（含 MAINTENANCE_RULES.md 是否更新、更新了哪一节）；
- commit hash；
- 部署到哪、是否重启；
- 验证证据（真实浏览器/关键路径/日志）；
- 回滚方法；
- 《变更执行记录》里追加的一行。
缺任何一项，都视为未完成。

【禁止事项】
- 不许跳过 review 直接部署；
- 不许只部署不提交、只改线上不改仓库；
- 不许用“应该可以/理论上没问题”代替验证；
- 不许在未确认时批量改数据、批量发通知；
- 不许把密钥、密码、token 写进代码或聊天记录。

如果项目没有现成的测试/部署命令，先问我，不要自己猜。

## 本项目信息（2026-10-21 建立，随本次功能 PR 更新）

### 项目与 Git 流程

- 产品：墨析 OCR 工作台，本机桌面外壳 + Web 阅读/扫描界面 + Python OCR 后端。
- 唯一目标仓库：<https://github.com/cpcboy/ximo-ocr>。
- 用户要求：后续任何改动先提交 PR 到该仓库，review、测试通过后合并，再从已合并版本发布生产；禁止直接修改生产来代替仓库变更。
- 初次检查时本地及远端均无提交；已按授权创建空初始化 `af9c418`，维护文档 PR #1 已合并为 `8feb90175a46810a834ddd41904fe6c3808b3354`。不得把现有构建目录或运行数据当作源码首次提交。
- 首次文档须独立提交，消息为 `docs: 建立维护铁律与执行规范`。用户仅授权一次不含文件的 main 初始化；之后所有文档和代码修改均经 PR 合并。
- 交付必须区分“构建成功”“已发布”“目标机器真实验收通过”，不能相互替代。

### 指令文件检查

首次检查：根目录仅存在 `README.md`；不存在 `AGENTS.md`、`CLAUDE.md`、`.cursor/rules`、`.github/copilot-instructions.md`、`CONTRIBUTING.md`、`MAINTENANCE_RULES.md`。

本次新增 `AGENTS.md` 作为项目 AI 入口；原有 README 不覆盖。首次 Git 导入前仍须审查已有源码和文档是否含个人数据、凭据、绝对私人路径和构建产物。

### 测试命令

以下入口可在源码核对；具体执行结果见 `MODEL_DOWNLOAD_VALIDATION.md`，不以列出命令代替测试。均在项目根目录执行。

| 命令 | 来源及范围 |
| --- | --- |
| `.venv/bin/python -m pytest -q` | `LOCAL_VALIDATION.md`；Python 回归测试。使用隔离临时数据，不操作用户历史任务。 |
| `.venv/bin/python -m py_compile backend/*.py windows/*.py scripts/deploy_macos.py` | Python 语法检查。 |
| `npm run lint` | `package.json`；前端静态检查。 |
| `npm test` | `package.json`；先构建，再运行 `node --test tests/*.test.mjs`，覆盖页面契约、源码来源、许可收集。 |

依赖安装：`npm ci`；Python 开发环境按 `requirements.txt` 安装后补 `pytest httpx`。CI 使用 Windows 引导依赖运行可跨平台测试，不需要下载模型。`npx tsc --noEmit` 的遗留 Cloudflare 示例类型错误尚未修复，不能登记为通过。

Windows 的真实安装、杀毒软件扫描、首次下载、真实 OCR、退出后进程/显存释放，必须按 `WINDOWS_CODEX_HANDOFF.md` 与 `WINDOWS_TEST_REPORT_TEMPLATE.md` 留证。Mac 的桌面窗口、系统选文件框和导出保存框也必须真实操作；不能只以自动化单元测试代替。

### 构建命令

| 平台/目标 | 命令 | 当前输出/限制 |
| --- | --- | --- |
| 网页 | `npm run build` | `dist/standalone/`。 |
| Mac 应用 | `./mac-app/build-app.sh` | `build/macos/墨析 OCR 工作台.app`；须先构建网页。1.3.0 改为校验固定便携 Python/Node，运行时依赖内置；最低 macOS 14、Apple Silicon。不能以构建替代干净机器验收。 |
| Mac DMG | `./mac-app/build-installer.sh` | 仅接受已合并到 `origin/main` 的干净源码；输出 `build/macos/output/MoxiOCR-macOS-arm64-1.3.0.dmg` 及 SHA-256。已从 PR #2 合并提交生成并只读挂载验证，见 CANDIDATE_DELIVERY.md；仍非生产发布。 |
| Windows 安装包（在 Mac 构建） | `./windows/build-installer.sh` | `build/windows/output/` 下 EXE 和 SHA-256；需已构建网页及 NSIS。 |
| Windows 安装包（在 Windows PowerShell 构建） | `.\windows\build-installer.ps1` | 来源于已有 Windows 交接文档；完整构建和干净机器兼容性须本次复验。不自行修改或绕过执行策略。 |

构建入口和限制详见 `DEPLOYMENT.md`。前端内保存源码摘要；打包开始/结束均核对，不允许拿旧 dist 打新包。未提交候选标记 `UNCOMMITTED-`，禁止生产发布。

**构建前备份门禁：** Mac 构建脚本会重建旧构建 `.app`，Windows 两份构建脚本会重建 stage，发行 output 的同名文件存在时拒绝覆盖。执行任何构建前，先把仍需保留的旧安装包、`.app` 和 SHA-256 清单复制归档到构建脚本不会清理的位置，核验可回读并记录准确路径及哈希。只有确认回退点安全后才能运行构建；不能等到“发布前”才备份构建目录中的旧产物。

### 部署命令与验证地址

- 用户已确认通过 GitHub Releases 分发合并后版本，并备份更新本机 Mac。新增 `scripts/deploy_macos.py` 提供 snapshot / install / rollback，已做隔离合成测试；实际安装参数、备份、漂移检查和发布步骤见 `DEPLOYMENT.md`。尚未对生产执行 install。
- 当前已安装 Mac 应用：`/Applications/墨析 OCR 工作台.app`，检查时版本 `1.2.2`（build `5`）。更新前必须备份整个应用并记录 SHA-256/源版本，确认没有未纳入 Git 的生产代码改动。
- 本机工作台地址：`http://127.0.0.1:3000/`，来源于 Mac 外壳与 Windows 启动器。
- 本机后端地址：`http://127.0.0.1:18765/`；`/api/readyz` 和 `/api/health` 是辅助检查，不是用户路径验收。
- 不发布为公共 Web 服务，不扩大监听地址或 CORS 权限。用户确认的 Origin/Host 拦截见下方第 5 项；任何新的访问控制调整均须先确认。
- 任何安装包发布前须确认不含模型权重、源文档、OCR 结果、日志、凭据、开发缓存；模型下载单独由用户在应用中发起。

### 文档路径

- 维护制度与执行记录：`MAINTENANCE_RULES.md`。
- AI 强制入口：`AGENTS.md`。
- 功能和使用：`README.md`。
- 已有测试记录：`LOCAL_VALIDATION.md`、`MAC_READER_VALIDATION_2026-07-30.md`。
- Windows 交接与验收：`WINDOWS_CODEX_HANDOFF.md`、`WINDOWS_TEST_REPORT_TEMPLATE.md`、`START_HERE-WINDOWS-CODEX.txt`、`windows/Windows安装说明.txt`。
- 变更记录：`CHANGELOG.md`；构建、发布、漂移检查及回滚：`DEPLOYMENT.md`；本次真实验收与未完成项：`MODEL_DOWNLOAD_VALIDATION.md`。
- 开源授权及依赖说明：`LICENSE`、`THIRD_PARTY_NOTICES.md`；未经授权不得更改许可证口径。
- 阶段候选交接：`CANDIDATE_DELIVERY.md`，含实际源码 SHA、包哈希、验证证据、未完成项与生产状态。
- 候选预览发行说明：`RELEASE_CANDIDATE_v1.3.0-rc.1.md`；仅供 GitHub Pre-release 分发，不替代完整验收。

### 回滚方式

- 文档：通过 revert PR 回退本次文档提交，不直接推送 main；如用户铁律未被撤销，不得通过回退规避执行规范。
- 应用：发布前保留旧安装包和旧 `.app` 备份，记录准确路径、哈希和版本。停止本应用后恢复旧应用，不覆盖/迁移用户数据和模型目录；按原版本真实用户路径复验。
- 发布：只回退已合并、可审计的版本；GitHub Release、安装包版本、源码 commit、变更文档必须对应。具体部署/回滚命令见 `DEPLOYMENT.md`。首次 1.2.2 基线应用备份在本机忽略目录 `.maintenance-backups/2026-10-21-model-download/`，有完整清单，禁止把备份打进包。
- 本任务未经额外授权不得修改生产扫描数据，也不进行数据库迁移。验证采用合成文件及隔离数据目录。

### 用户已确认的项目口径（2026-10-21 至 2026-10-22）

用户逐项确认以下八项。这些是本项目范围内的明确授权，不扩大其他权限。

1. **底线 C 的项目例外：** 墨析是离线桌面应用，继续在本机应用数据目录保存扫描原件、识别结果和阅读笔记；这些数据绝不提交 Git、上传到仓库或放入安装包。原有数据不迁移、不批量改动。模型保存在应用管理的本机模型目录，安装包不附带权重。
2. **一次性空仓库初始化：** 允许仅向 main 写入一个不含文件的初始化提交，之后文档、代码及发布流程修改全部 PR → review/测试 → 合并 → 发布。
3. **平台模型：** Apple Silicon Mac 下载 `LoJexLLM/Unlimited-OCR-MLX`，Windows 下载 `baidu/Unlimited-OCR` 的 NVIDIA/PyTorch 版本，界面必须说明平台区别。不得将 MLX 标成可在 Windows 使用。
4. **发布范围：** PR 合并后发布 GitHub Releases 的 Mac/Windows 安装包，并备份更新本机 `/Applications` 中的墨析；不自动安装到家里的 Windows。Windows 安装包必须明确标注实机验证范围，构建结果不能代替实机结论；未验收部分只能称候选版。
5. **本机 API 来源拦截：** 用户同意只允许墨析 localhost/127.0.0.1 页面发起操作，拒绝外部网页来源；保留 App 内部无 Origin 的本机调用，不扩大现有 CORS。测试正常操作、外部 Origin、伪造 Host、null Origin、跨站 Referer/Fetch Metadata。此规则不是本机其他进程的身份认证，不应声称能阻止恶意本机程序。
6. **项目许可证：** 用户同意墨析按 AGPL-3.0 开源发布，落地为 `AGPL-3.0-only`，仓库提供源码并保留依赖许可说明。此授权不包含上传用户扫描数据，不改变模型及第三方代码自身许可。
7. **本次阶段交付（后续明确确认）：** 由于 6.7 GB 模型官方下载较慢，用户选择先提交并合并 PR、生成 Mac/Windows 候选安装包；正式发布和本机更新等全量验收通过后再做。本次不创建正式 Release、不更新 `/Applications`，不自动安装远端 Windows；必须如实报告未完成项。
8. **候选预览版分发（2026-10-22 追加确认）：** 在再次告知全量 OCR 和 Windows 实机尚未验收后，用户明确回复“先发布候选预览版”。仅授权在本仓库创建标为 Pre-release、非 Latest 的 `v1.3.0-rc.1`，分发既有已校验的 Mac/Windows 候选包及 SHA-256。版本 tag 固定为包内来源 `2db71b41864cdc3ec3222279f4cf07f2a875e459`，不得把后续文档提交冒充包的构建来源。先将本次发布文档经 review、PR、CI 合并，再上传、校验并公开；发布后浏览器验证和执行记录另经文档 PR 回填。没有授权正式发布、替换/重启本机 App、操作远端 Windows 或豁免原有完整验收门禁。

平台依据（2026-10-21 核对）：[MLX 模型卡](https://huggingface.co/LoJexLLM/Unlimited-OCR-MLX) 标明 Apple Silicon、macOS 14+；[原版模型卡](https://huggingface.co/baidu/Unlimited-OCR) 的 Transformers 推理示例面向 NVIDIA GPU。这不是 Windows 实机验收结果。

## 变更执行记录

| 日期 | 变更内容 | review 结论 | 文档更新 | commit | 部署 | 验证证据 | 回滚方式 |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-10-21 | 建立维护铁律与 AI 入口，用户已确认存储/初始化/平台/发布四项口径 | 已自查及独立对抗 review；P2 构建前备份时机已修复；四项确认记录复核通过；剩余 P0/P1/P2=0 | 本文件：用户原文、本项目信息、构建前备份、用户确认口径、执行记录；新增 AGENTS.md | `0f4828e831c124422c264932a296029deea91aa7`；PR #1 合并 `8feb90175a46810a834ddd41904fe6c3808b3354`；空初始化 `af9c418` | 仅文档已合并；应用未部署、未重启 | 只读核对源码命令、App 版本、模型卡及远端空仓库；diff 空白检查通过；未做功能验收 | revert PR；不修改应用与业务数据 |
| 2026-10-21 | App 内分平台下载模型、便携运行时、来源拦截、安装器和 AGPL 开源说明 | 下载/打包及许可补充末轮独立 review P0/P1/P2=0；CI CRLF 与 NSIS 路径/编码修复均已独立复核 | README、CHANGELOG、DEPLOYMENT、MODEL_DOWNLOAD_VALIDATION、Windows 交接；本文件命令、确认第 5/6/7 项、执行记录 | 功能 `a76a7e9aa8b137ec217546430ac16ba17405c160`；PR #2；合并与构建记录后续文档 PR 回填 | 按最新授权仅交付候选；生产 1.2.2 未替换；未发布 Release | 57 Python、7 前端/来源/许可测试通过；PR 两轮 CI 暴露 CRLF/NSIS 问题，已修复待重跑；真实 Mac 下载/暂停/退出/续传、文本导入/阅读/完整 ZIP 导出通过；全量模型 OCR、Windows 实机未验收；系统诊断及边界见验收记录 | 保留旧 App/源码备份；未部署无需回滚；部署后的回滚按 DEPLOYMENT.md |
| 2026-10-22 | 合并 PR #2、从合并源生成 Mac/Windows 候选、只读 DMG 复验并补齐交接 | 代码末轮及证据文档独立复核 P0/P1/P2=0 | 新增 CANDIDATE_DELIVERY；README、MODEL_DOWNLOAD_VALIDATION；本文件构建结果、文档路径与本行 | 候选源/PR #2 合并 `2db71b41864cdc3ec3222279f4cf07f2a875e459`；证据回填为后续文档 PR | 按用户第 7 项确认不部署；生产 1.2.2 build 5 未替换/未重启；无正式 Release | PR CI 39736384496、main CI 39736916274 全成功；DMG 签名/镜像、Windows 解包/来源、真实续传/阅读/完整 ZIP/退出通过；哈希和证据见 CANDIDATE_DELIVERY；全量 OCR、Windows 目标机与系统诊断待验 | 旧 App/清单/源码备份保留；本次无需生产回滚；源码仅 revert PR，未来 App-only rollback 见 DEPLOYMENT |
| 2026-10-22 | 按追加授权分发 v1.3.0-rc.1 候选预览版；应用代码与包不变 | 自查及独立发布 review 完成；P2 已有 tag 来源校验已补齐并复核，剩余 P0/P1/P2=0 | 本文件确认第 8 项和本行；README、CHANGELOG、DEPLOYMENT、CANDIDATE_DELIVERY、MODEL_DOWNLOAD_VALIDATION；新增候选发行说明 | 安装包源 `2db71b41864cdc3ec3222279f4cf07f2a875e459`；本次文档提交及发布证据后续回填 | 计划仅 GitHub Pre-release，非 Latest；不更新/重启本机或远端 Windows | 本轮 57 Python、lint、diff 检查通过；两个包 SHA-256 与既有记录一致，Mac 签名/DMG 校验通过；上传/浏览器/回读未执行，不记完成 | 草稿校验失败不公开；公开后异常标记撤回并保留 tag/原包，不动用户数据；详见 DEPLOYMENT |
