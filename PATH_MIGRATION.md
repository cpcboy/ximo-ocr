# 本机源码目录迁移（2026-10-23）

本次用户指定把开发项目从 `~/Downloads/unlimited-ocr-studio` 迁至 `~/cpcsoft/OCR`，同步更新相关路径。此为**源码工作区迁移**，不是 App 更新、模型迁移或新版本发布；执行结果以迁移回执和本次 PR 的最终验证评论为准，不将下列计划提前记为通过。

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
