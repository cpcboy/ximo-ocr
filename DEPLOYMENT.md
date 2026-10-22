# 构建、发布与回滚

唯一仓库：https://github.com/cpcboy/ximo-ocr 。先读 `MAINTENANCE_RULES.md`；以下入口已落入源码，具体某次是否执行通过以变更执行记录和验收记录为准，不以文档命令代替验收。

用户已确认本次先交付已合并源码与候选包。下文 install / 正式 Release 步骤本次不执行；等待全量模型 OCR 等正式验收完成再进入生产发布。

## 发布门禁

1. 主题分支改动 → 自查 diff → 独立对抗 review（P0/P1 清零，P2 逐条处理）→ 文档 → 提交 PR。
2. Python、前端测试与 CI 通过后合并；生产只用与 `origin/main` 一致的干净 checkout。不要直接改 `/Applications` 内文件。
3. 构建前保存需要保留的旧 `.app`、EXE、DMG 及哈希，备份必须在 `build/` 外。脚本会重建 stage / `.app`，但不删除已存在的同名发行安装包，须先归档。
4. 核对没有扫描文件、OCR JSON、模型权重、日志、凭据进入 Git 或安装包。用隔离数据完成用户路径；候选构建不等同于生产。
5. Mac 全量模型首次下载及 OCR 未验证，或任何已知失败未解决时，停止生产部署。Windows 未在目标机器验收时只允许明确标记 candidate。

## 测试

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

本次维护开始的准确清单和旧版位于本机忽略的 `.maintenance-backups/2026-10-21-model-download/`。这些是本机回退材料，不提交 Git/Release。首次基线为 1.2.2 build 5；没有执行 install 前，生产仍是该版本。

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
