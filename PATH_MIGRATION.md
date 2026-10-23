# 本机源码目录迁移（2026-10-23）

本次用户指定把开发项目从 `~/Downloads/unlimited-ocr-studio` 迁至 `~/cpcsoft/OCR`，同步更新相关路径。此为**源码工作区迁移**，不是 App 更新、模型迁移或新版本发布；执行结果以迁移回执和本次 PR 的最终验证评论为准，不将下列计划提前记为通过。

**实际状态：迁移已完成。** 2026-10-23 从 PR #13 已合并源执行，下文“实际验收”记录结果；后续证据文档的提交不冒充测试时的源码来源。

## 路径口径

| 对象 | 迁移后位置 / 处理 |
| --- | --- |
| 唯一在用的本机源码工作区 | `~/cpcsoft/OCR`，含原 `.git`、源码、开发依赖与忽略目录 |
| Git 远端 / 包名 | `https://github.com/cpcboy/ximo-ocr` / `unlimited-ocr-studio`，均不改名 |
| 开发 venv | 新根目录下 `.venv`；只替换已核对的旧根路径，不升级 Python 或依赖 |
| 开发数据、证据、旧构建和回退备份 | 原 `data/`、`test-results/`、`build/`、`.maintenance-backups/` 随根目录原样移动，不改业务内容、不重写历史审计 |
| 已安装 Mac App | `/Applications/墨析 OCR 工作台.app` 不变；不是指向源码的快捷方式 |
| 已安装 App 的扫描、模型、日志、回退点 | `~/Library/Application Support/墨析 OCR 工作台/` 不变；旧 LM Studio 模型目录不变 |
| Windows 及 GitHub Releases | 不变，不安装、不重新发布 |
| 已交付 DeepSeek ZIP / SHA-256 / 回执 | 保持原文件和原提交，不覆盖成新来源；接手当前工作区以本文件及最新 main 为准 |

源码 `.command`、Mac/Windows 构建脚本、Python 配置、前端来源检查均从脚本/模块位置推导项目根，不写死这个人的目录。迁移不批量改包名，不把私人绝对路径注入运行代码，也不改已签名 App 的内容。

## 已发现的路径引用及例外

- 开发环境需修复 **8 个文件**：`.venv/pyvenv.cfg`、`.venv/bin/activate`、`activate.csh`、`activate.fish`、`pip`、`pip3`、`pip3.11`、`pymupdf`。备份后只精确替换旧源码根前缀；保留文件权限、版本、现有 site-packages 和系统 Python 链接。
- `build/` 中历史便携 Python 的部分 console-script shebang、已签名 App 和不可变回退包仍含构建时旧路径。实际启动入口使用应用内 `python3 -m uvicorn` / 内置 Node，不执行这些 shebang。为保留签名、来源与历史校验值，本次不改写它们，不宣称全盘已无旧路径字符串；也不借迁移修复未使用的历史 CLI。
- `data/` 元数据仅做旧前缀检索和完整性核对，不打开历史任务做测试。发现仍依赖旧位置的业务路径即停止，先取得单独的数据变更授权。
- 旧日志、基准结果、备份 manifest、历史 Git 内容及已交付 ZIP 是事实记录，不做全局替换。无独立 Codex 项目注册指向旧源码根，故不修改整个 Downloads 项目或聊天历史。未来打开项目选择新目录。

## 执行与验收顺序

1. 读维护铁律；核对旧工作区干净、远端 main、目标为空且不是符号链接、同卷；核对没有进程从旧树执行或把它当 cwd、3000/18765 没有服务。未知进程先停止迁移，不批量 kill。
2. 本次路径文档先自查、独立对抗 review、PR、Linux/Windows CI 通过并合并。既有 CI 可能生成 Windows 测试 artifact，不是新发行包。
3. 在工作区之外建立私有迁移审计目录，保存合并 SHA、全树文件 SHA-256 / mode / 符号链接清单、8 个 venv 文件的逐字备份。扫描不追随符号链接；旧根绝对符号链接需单独处置，不能带病迁移。
4. 再次核对目标为空且同卷，移除**这个已确认的空目录**，同卷 rename 旧根为新根；不递归删除、不覆盖目标文件、不留依赖旧目录的兼容软链接。立刻与迁移前全树清单逐项比对，包含 `.git`、业务文件、产物和备份。核对通过后才修复 8 个 venv 文件；该修改只存在本机 ignored 环境，不进入 Git/安装器。
5. 新目录执行 Python 回归、lint、前端构建和 Node 测试；构建前保存旧 `dist`、核对回读。核对 shell 激活后的 VIRTUAL_ENV、Python sys.prefix、pip/PyMuPDF CLI 都指向新根；不更新依赖，不重建旧 `.app`、DMG、EXE。
6. 浏览器验收用全新隔离 `OCR_STUDIO_DATA_DIR`、`OCR_STUDIO_SUPPORT_DIR`、`UNLIMITED_OCR_MODEL_DIR`、`OCR_STUDIO_DISABLE_LEGACY_MODEL=1`。从新目录启动前后端，只上传合成 TXT，验证完成→阅读→导出完整包；无模型下载/加载，不用历史任务。检查日志及退出后本次进程释放，保留截图和测试摘要，清理合成产物可用可恢复移动。

已安装 App 本次不启动、不退出、不替换。迁移后的源码网页路径验收不冒充原生 App、真实图片 OCR 或 Windows 实机验收。最终回执记录准确合并 SHA、CI、全树对照、8 文件变化、旧 `dist` 备份、浏览器证据和未测边界。

## 回滚

若路径/完整性验收失败，停止本次测试进程，保留失败证据。先核对旧根不存在、没有新用户写入及未知进程；如果已有后续改动，停止并确认合并方式，禁止覆盖。

仅把本次 8 个 venv 文件从已核验的私有备份恢复，再把整个源码目录同卷移回原位置。若需恢复旧前端，把新 `dist` 保留到独立目录，再恢复备份，不动 `data/`、模型或安装版。文档需要回退时另走 revert/修正 PR；不 reset 远端、不重新生成旧 ZIP、不改历史包 hash。安装版没有变更，无需 App-only rollback。

## 实际验收（2026-10-23）

- 迁移/网页实测源：[PR #13](https://github.com/cpcboy/ximo-ocr/pull/13) 合并 `6cb53be3b00fe9c517a23107e7b2ebd1d29e2e53`，文档提交 `f13f2efbda5ec04a7937d782912bb3f367f649e6`。[PR CI 39984031532](https://github.com/cpcboy/ximo-ocr/actions/runs/39984031532) 与合并 main 的 [CI 39984829286](https://github.com/cpcboy/ximo-ocr/actions/runs/39984829286) 均已回读 Linux/Windows completed/success，源 SHA 相符。
- 目标原为空真实目录、与旧根同卷；无旧树活动进程、3000/18765 无监听。rename 后根目录 inode 保持，旧根不存在，无旧位置软链接。
- 移动前后 **112,696 条目 / 98,937 文件**严格核对零差异（包括 `.git`、内容 SHA-256、文件 mode、符号链接目标），核对发生在环境修复/测试之前。
- 随后精确修复 8 个 venv 文件；激活后的 `VIRTUAL_ENV`、Python `sys.prefix` / `PROJECT_ROOT`、`pip --version` 都指向新根，`pymupdf --help` 可执行；bin/config 中旧前缀为零。未升级 Python 或任何依赖。
- 新根：**68 Python 测试通过**（5 条既有 SWIG 告警）、lint 通过、前端构建及 **11 Node 测试通过**。仍不把遗留 Cloudflare 类型问题登记为解决。
- 测试后核对 `data`、`build`、`.maintenance-backups`、`test-results` 共 **70,091 条目**无变化；8 文件最终类型/权限/替换内容正确；旧 dist 备份 **3,316 条目**及根目录类型/权限与原版一致。已安装 App 前后清单完全相同、严格签名复验通过，仍为 build 6 / 源 `b7d29292...`。
- 真实内置浏览器从新根构建的服务执行：点击“选择文件”→合成 `migration-smoke.txt`→1 页完成→阅读器正文/中文标记可见→实际下载完整结果包。ZIP 4 项中文文件名/CRC 正常、原件字节相同、TXT/JSON 标记保留，SHA-256 为 `d76fbb46c6122bd2782ed58e5242db390e007115cd8ae2f76e6b05a37a144c6c`。
- 浏览器 console error/warn 为空，前后端日志无 ERROR/Traceback/5xx；外部 Origin 请求下载模型被拒绝为 **403**。浏览器关闭后只读 client/status 返回 `connected=false`；随后只停止本次两进程，后端正常 shutdown、两端口无监听。隔离模型目录未创建，未下载/加载模型，未启动/退出已安装 App。
- 独立 review 修复两项 P2：漏列 PyMuPDF shebang；最终审计漏比目录根/venv 权限。均复核关闭；最终证据、截图、ZIP、App 清单/签名及 70,091 保护条目的第二遍独立 hash 复算均通过，末轮 P0/P1/P2=0。

原始证据、8 文件原件和旧 dist 位于本机私有 `~/cpcsoft/.ocr-migration-20261023/`：`before.json`、`move-verification.json`、`venv-rebase.json`、`final-verification.json`、`venv-original/`、`dist-before/`、`installed-app-before.json` / `installed-app-after.json`、`python-test.log`、`npm-test.log`、`backend.log`、`frontend.log`、`reader.png`。不提交这些清单、用户数据、旧产物或截图。合成任务仅用于隔离验收，可恢复清理；迁移备份须保留。

验证边界：本次没有图片模型推理、原生 App 更新或 Windows 实机安装；只证明新源码位置的环境、构建、合成文本真实路径及原文件保全。已发布 rc.2 与已交付 DeepSeek ZIP 原位不变，旧包来源和哈希仍有效。
