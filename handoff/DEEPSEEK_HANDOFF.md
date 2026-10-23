# 墨析 OCR · 详细技术交接

核对日期：2026-10-23；受众：接手的 DeepSeek / 本地执行代理 / 人工 reviewer。先读根目录 [接手入口](../START_HERE-DEEPSEEK.md)。本文是现状和操作边界，不是部署授权。

## 1. 产品目标与当前状态

墨析是本机批量 OCR、结果校对与文档阅读工具。用户希望拖入不同类型文件，逐页识别，保留表格结构，编辑/搜索/阅读并导出完整结果包；扫描队列结束后卸载模型，退出 App 后释放服务资源。模型下载由用户在 App 内点击触发，不随安装器携带，也不把文件发送至外部 OCR 服务。

用户最初用 LM Studio 下载 MLX 模型；现版本可管理自己的模型。**不需要 LM Studio 运行或开放 API**，不应把现有引擎改成 LM Studio 代理。OCR 输出的 `<table>/<tr>/<td>` 是结构化内容，不是待执行程序；前端必须经安全过滤呈现，仍保留原始文本。

### 1.1 源码、公开包、安装版不能混为一谈

| 对象 | 精确来源 / 版本 | 已确认状态 |
| --- | --- | --- |
| 交接功能基线 | `352665be7f147474af1cf93f522958e3972cb052` | PR #11 合并到 main，含 MLX 优化；本次只追加交接文档 |
| PR #11 最终 CI | [39843033560](https://github.com/cpcboy/ximo-ocr/actions/runs/39843033560) | 成功；不是新的安装包验收 |
| 功能基线 main CI | [39843742424](https://github.com/cpcboy/ximo-ocr/actions/runs/39843742424) | 已回读 completed/success，head 为上述功能基线 |
| 公开 rc.2 | `3e9a7e2ea2bc33fd58cafd33520a1928599a28c3`，Mac 1.3.0(7)、Windows 1.3.0.2 | Pre-release；阅读配色修复已打包，MLX 优化未打包 |
| 交接发起机器上的 Mac 安装版 | `b7d29292c18aa30fa00e4aef9f33ca57663100ad`，1.3.0(6) | 只读核对 Info.plist / SOURCE_COMMIT；本次未启动、替换或重启 |
| 正式版 / Windows 10 Pro 实机完整验收 | 无本次通过证据 | 不得用候选发布、CI 或 Mac 测试替代 |

参考：[PR #11](https://github.com/cpcboy/ximo-ocr/pull/11)、[rc.2](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.2)、[rc.2 验证](../RC2_VALIDATION.md)、[本机更新记录](../LOCAL_PREVIEW_UPDATE.md)。文档内日期和“当前”是各次维护快照；例如 rc.2 的“图片 OCR 未验”指**那一批安装包**，后续源码 MLX 实测通过不能反向替 rc.2 补验。

最终交接 ZIP 是后续文档 PR 的合并树，不是从旧安装目录反向导出的源码。使用 ZIP 注释和交付校验记录确定最终打包 SHA；继续开发时 `git fetch` 后核对最新 main，存在新改动先 review 差异，不覆盖他人工作。

### 1.2 公开安装器校验（历史包，不随交接 ZIP 附带）

| 文件 | 字节数 | SHA-256 |
| --- | ---: | --- |
| `MoxiOCR-macOS-arm64-1.3.0-rc.2.dmg` | 282825180 | `d96cfa4be5218c0056b2115527dd370687e1518b53715c08d1d901e33f1e844b` |
| `MoxiOCR-Windows-x64-1.3.0-rc.2-candidate.exe` | 52748024 | `f39679299d48ace609eb9276087c2840f0845789ec7d45fa82c8fcc22172c678` |

交接时已回读 GitHub 资产 digest/size；本次没有重新下载安装器。之前真实浏览器下载和独立公开回读证据见 RC2_VALIDATION，不冒记为本次重验。Mac 仅 ad-hoc 签名、无 Developer ID 公证；Windows 无商业代码签名。不能承诺不会被 Gatekeeper、SmartScreen 或杀毒软件拦截。

## 2. 架构与阅读路线

```text
Mac Swift / WKWebView                  Windows NSIS EXE / Python 启动器 / Edge
              └────────── 本机网页 127.0.0.1:3000 ──────────┘
                               │
                      FastAPI 127.0.0.1:18765
                               │
        上传 → 文件转换/分页 → 串行任务队列 → OCR 或直接提取文本
                               │
             Mac MLX/Metal                  Windows PyTorch/CUDA
                               │
          本机任务目录（原件、预览、job.json、阅读状态、导出）
```

| 模块 / 入口 | 职责与注意事项 |
| --- | --- |
| `app/page.tsx` | 工作台、上传/批量任务、结果渲染/编辑/导出、模型下载、心跳；修改上传需测系统文件框和拖放两条路径 |
| `app/document-reader.tsx`、`app/globals.css` | 阅读器、原图/正文、搜索、书签/笔记/主题；深色主题要实际看文字/表格对比度 |
| `backend/app.py` | API、任务队列、互斥、导出、阅读准备、客户端生命周期；导入模块会建立 JobStore，不能用生产路径随意试 import |
| `backend/documents.py` | PDF/图片/文本/Office/ZIP 转换；多页和档案边界在此；LibreOffice 是外部可选依赖 |
| `backend/store.py`、`config.py` | JSON 文件任务存储与路径；不是数据库迁移入口，详见第 4 节 |
| `backend/engine.py`、`model_compat.py` | Mac 自定义 MLX 模型加载、兼容层、推理、防重复；不要把它替换成通用聊天接口 |
| `backend/mlx_performance.py` | 已合并的闲置缓存软阈值回收，仅 Mac；不要重复实现或另加清理线程 |
| `backend/windows_engine.py` | NVIDIA 检测、PyTorch CUDA 推理；不支持把 MLX 权重当 Windows 模型 |
| `backend/repetition.py`、`repair_results.py` | 重复诊断/修复；历史文件修复必须另授权、先备份，不能对用户目录批处理 |
| `backend/model_catalog.py`、`model_download.py`、`backend/models/*.json` | 固定模型 revision / 大小 / 哈希、下载续传、校验和运行时安装；JSON 清单必须随源码保留 |
| `mac-app/OCRStudioApp.swift`、`runtime-start.sh`、`runtime-stop.sh` | 原生选文件/下载保存、启动和退出；不能只测浏览器代替 WKWebView |
| `windows/windows_launcher.py`、`backend_bootstrap.py`、`*.nsi` | 启停、心跳、路径、NSIS 安装/卸载；旧停止 LNK 不得重新引入 |
| `scripts/build_frontend.mjs`、`build_identity.mjs`、`collect_notices.mjs` | 独立网页构建、Git 来源摘要、许可证；修改文档也会改变 source digest，须重建网页 |
| `scripts/deploy_macos.py` | snapshot / install / rollback；保护签名、漂移、来源和 App-only 回退 |
| `scripts/benchmark_mlx.py` | 自造五图、AB/BA、完整 token/文字/诊断一致性；需要真实 Git 历史和明确模型路径 |
| `.github/workflows/checks.yml`、`tests/` | Linux/Windows CI；CPU 回归、前端契约/主题、NSIS 编译；不下载模型，不代表 GPU OCR 实测 |

前端包名仍为 `unlimited-ocr-studio`，产品中文名为“墨析”，仓库名为 `ximo-ocr`；这是既有命名，不需借交接批量重命名。前端用 React 19 / Next 风格目录，但构建入口实际是 **vinext / Vite**，不能换成 `next start`。

`db/`、`drizzle/`、`worker/`、`examples/d1/`、`.openai/hosting.json` 是模板/构建相关遗留，当前 d1/r2 均 null；不是本地 OCR 业务存储。构建仍引用其中部分文件，不能直接删掉。不要因为存在 Drizzle 就运行数据库迁移、建云数据库或部署公共站点。

## 3. 环境与模型

| 项目 | 当前已固定的口径 |
| --- | --- |
| Node | package 要求 >=22.13.0；CI/便携运行时固定 22.23.2，优先与其一致 |
| Python CPU 测试 / Windows | CI 3.12；Windows 内嵌 Python 3.12；不需安装 MLX 来跑 CPU 回归 |
| Mac 安装版 Python | `mac-app/prepare-runtime.sh` 固定便携 **3.11.17**；不要把 CI 3.12 或开发 venv 当作安装版 |
| Mac 依赖 | `mac-app/requirements-runtime.txt`：MLX/MLX Metal 0.29.3、Transformers 4.57.1；其余版本以该文件为准 |
| Windows 引导依赖 | `windows/requirements-bootstrap.txt`；推理包稍后由下载管理器安装到可写目录 |
| Windows 推理包 | PyTorch 2.10.0、torchvision 0.25.0、CUDA 12.8 wheel、Transformers 4.57.1；需 NVIDIA 和兼容驱动，尚无目标机通过证明 |
| Mac 模型 | `LoJexLLM/Unlimited-OCR-MLX`，revision `267d7adcbcd3730fdffb1eefd70ef6f486fbfc92`；Apple Silicon / macOS 14+，MLX 通过 Metal GPU 执行 |
| Windows 模型 | `baidu/Unlimited-OCR`，revision `07dea832e22aefee32ad281d4b80551282e1c168`；NVIDIA/PyTorch，不能换下载为 MLX |
| 模型大小 / 磁盘 | 约 6.7 GB 权重；运行时、临时下载、扫描和导出另占空间，不能把模型大小当全部空间需求 |
| Office | LibreOffice 另装，未打包；格式声明不等于 HEIC/Office 等在所有机器均实测成功 |

根 `requirements.txt` 仅是一般后端开发依赖，不等同于完整 MLX 运行时。Windows CPU/AMD/Intel Mac 没有本项目已验证的等效 OCR 方案，不应无提示静默切换。

管理下载时固定 revision 和逐文件哈希；完整校验后写 `.moxi-model-complete.json`，健康检查用 revision + 文件 size/mtime 快速核对，不是每次重算全文件 hash。模型目录含需执行的 Python 实现，所以不能只看权重存在就信任来源，不能把远端代码改为浮动 `main`。旧 LM Studio 兼容路径检查不等同于新管理目录的完整收据流程；后续扩展此路径须独立评估。

## 4. 数据、权限和生命周期：不能踩的边界

### 4.1 目录

| 类别 | Mac 安装版 | Windows 安装版 |
| --- | --- | --- |
| 程序 | `/Applications/墨析 OCR 工作台.app` | 默认 `%LOCALAPPDATA%\Programs\MoxiOCRStudio` |
| 支持根 | `~/Library/Application Support/墨析 OCR 工作台` | `%LOCALAPPDATA%\MoxiOCRStudio` |
| 任务、原件、预览、阅读状态、导出 | 支持根下 `data/jobs/` | 支持根下 `data\jobs\` |
| 管理模型 | `models/Unlimited-OCR-MLX` | `models\Unlimited-OCR` |
| 日志 / PID | `logs/` / `runtime/` | `logs\` / `runtime\` |
| 下载的 Windows AI 包 | 不适用，Mac 随 App 内置 | `ai-packages\` |

Mac 直接运行源码时默认数据是项目下 `data/`，默认模型却仍可能指向应用支持目录或旧 LM Studio。**验证必须在进程启动前同时明确数据、support 和模型路径**，不能仅改 cwd。`.env.example` 是占位模板；Python 配置读取进程环境，不能假定写 `.env` 就自动隔离。

主要变量：`OCR_STUDIO_DATA_DIR`、`OCR_STUDIO_SUPPORT_DIR`（Mac 外壳/模型默认路径）、`UNLIMITED_OCR_MODEL_DIR`、`OCR_STUDIO_DISABLE_LEGACY_MODEL=1`、Windows 的 `OCR_STUDIO_AI_PACKAGES_DIR`。支持的上传默认上限 1 GiB、默认最多 300 页，分别由 `OCR_STUDIO_MAX_UPLOAD_BYTES` / `OCR_STUDIO_MAX_PAGES` 配置。不要为测试扩大这些防呆限制。

Windows 原生启动器从 `%LOCALAPPDATA%` 组装支持根，**不是**设置 Mac 的 `OCR_STUDIO_SUPPORT_DIR` 就能隔离。Windows 原生验收使用用户确认的独立测试账户/虚拟机；在真实业务账户升级前另做备份和授权。

### 4.2 持久化副作用

- `JobStore` 用进程内锁，写 `job.json.tmp` 后替换 `job.json`；不是多进程数据库锁，不能同时起两套后端共用 data。
- 启动时会把部分中断任务（running/preparing/canceling）改回 queued，并排队处理。**“只启动看看”也可能改历史数据/重新识别**。
- `/api/jobs` 最多列 500 项，不能拿 API 列表代替部署前磁盘全量任务终态检查；不可解析元数据也须阻断，不得忽略后继续更新。
- 阅读准备 `POST /reader/prepare` 会持久化阅读版；原始 OCR 文本保留。阅读进度/主题/笔记也会保存，打开历史阅读器不是严格只读验收。
- 导出可能生成预览/exports 缓存；`DELETE /api/jobs/{id}` 会删任务目录。不能用历史任务做导出/删除回归。
- 用户批准的离线存储例外继续有效；不迁移数据库、不清空任务、不上传私有证据。诊断日志外发前脱敏。

### 4.3 API 与本机安全

| 接口 | 作用 / 副作用 |
| --- | --- |
| GET `/api/readyz` | 就绪辅助，不更新客户端心跳 |
| GET `/api/client/status` | 读取连接状态，不更新心跳 |
| GET `/api/health` | 状态、下载进度、转换器、模型；**会刷新心跳**，不能拿它持续轮询“网页已关闭” |
| GET/POST `/api/jobs` | 列表 / 上传排队；上传不是普通 JSON multipart，先读 page.tsx 与服务端请求协议 |
| GET `/api/jobs/{id}`；PUT `/api/jobs/{id}/pages/{index}` | 任务读取 / 修改页面文字 |
| POST `/api/jobs/{id}/reader/prepare`；GET/PUT `/api/jobs/{id}/reader-state` | 阅读准备、读取/保存阅读状态 |
| POST `/api/jobs/{id}/cancel`、`retry`；DELETE `/api/jobs/{id}` | 更改任务或永久删除；需针对合成任务验证 |
| GET `/api/jobs/{id}/download/{format}`；GET `/api/jobs/{id}/download/zip/package` | 单格式 / 完整结果包；原生下载不能让主页面跳成错误页 |
| POST `/api/model/load`、`unload`、`download`、`download/cancel` | 模型和下载控制；不能在接手核对时自动调用 |
| POST `/api/client/disconnect` | 页面关闭通知；刷新要与 Windows 宽限配合验证 |

服务只绑定 `127.0.0.1`；Host 只接受 localhost/127.0.0.1:18765，网页 Origin 只接受 localhost/127.0.0.1:3000。还检查 null Origin、跨站 Referer/Fetch Metadata；无 Origin 的本机外壳请求保留。该规则不是本机恶意进程身份认证。不扩 CORS、不改 `0.0.0.0`、不新增免鉴权公网入口。旧 4173 阅读器预览、8765 历史端口都不是当前生产地址。

任务队列结束会卸载模型；网页关闭由通知/心跳触发空闲卸载；Mac 最后窗口关闭/退出、Windows 启动器退出负责子服务。Windows 使用网页心跳而非 Edge 初始进程寿命，默认客户端超时 90 秒、关闭宽限 5 秒。正在计算的安全取消/卸载边界须实测，不能通过定时 `killall python/node` 实现。

## 5. 安全的接手与开发命令

### 5.1 DS-00 首轮只读核对

在已有 clone 根目录执行以下只读命令；不要在 ZIP 目录直接执行 Git 命令后绕过报错。

```sh
git status --short --branch
git remote -v
git log -5 --oneline
git rev-parse HEAD
git rev-parse origin/main
gh pr view 11 --repo cpcboy/ximo-ocr --json state,mergeCommit,url
gh release view v1.3.0-rc.2 --repo cpcboy/ximo-ocr --json isDraft,isPrerelease,targetCommitish,assets,url
```

remote 若含凭据只在本机检查并脱敏，不能贴入聊天。没有 GitHub 登录/工具权限时报告缺口，不寻找或复制原机 token。需要最新远端时可 `git fetch origin main`（只更新本地远端引用）；不得拉取覆盖未提交改动。

### 5.2 用户确认进入开发后，新 clone 的 CPU 回归

先选一个不存在的源码目录。下列 `ximo-ocr` 若已存在，停下检查，不覆盖、不清理它。

```sh
git clone https://github.com/cpcboy/ximo-ocr.git ximo-ocr
cd ximo-ocr
git switch -c docs-or-fix/your-ticket
```

分支名 `docs-or-fix/your-ticket` 只是示例，换成对应工单短名。完整重读 AI/维护文档、复述六步后再修改。测试使用锁文件，不先升级依赖；CI 基线为 Node 22.23.2 / Python 3.12。

Mac / Linux 的无模型测试环境（已有 `.venv` 则先核对，不覆盖）：

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r windows/requirements-bootstrap.txt pytest httpx
npm ci
.venv/bin/python -m pytest -q
npm run lint
npm test
```

Windows PowerShell（不需要激活脚本或绕过执行策略）：

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows/requirements-bootstrap.txt pytest httpx
npm ci
.\.venv\Scripts\python.exe -m pytest -q
npm run lint
npm test
```

这是与 CI 一致的 CPU 回归环境，**不具备 Mac MLX / Windows CUDA OCR 能力**。本机上次功能回归 68 Python + 11 Node、lint 通过；接手必须记录本次实际数量和日志，不照抄。Windows 未装 NSIS 时编译测试可能跳过；CI 安装 NSIS 后强制补跑。`npx tsc --noEmit` 有已知模板类型错误，不是已通过门禁，不通过删除测试来消除。

`npm test` 会重新构建 `dist`。在原开发树运行任何构建前先保全仍需保留的构建产物；新 clone 无旧产物。CI Windows 构建的 artifact 仅候选、保留 7 天，不是自动发布。

### 5.3 隔离浏览器验证 / 原生验证

此段是后续工单方案，不是本次交接要求自动执行。先确认原应用没有未保存编辑或活动任务；需要退出用户 App 时先确认。不能抢占/杀掉 3000 或 18765 的未知进程，也不能私改安全白名单来换端口。

Mac 源码后端可在全新临时目录，用进程级 `OCR_STUDIO_SUPPORT_DIR`、`OCR_STUDIO_DATA_DIR`、`UNLIMITED_OCR_MODEL_DIR` 和 `OCR_STUDIO_DISABLE_LEGACY_MODEL=1` 启动 `python -m uvicorn backend.app:app --host 127.0.0.1 --port 18765`；前端先按当前源构建，再从 `dist/standalone` 用 `PORT=3000 HOST=127.0.0.1 node server.js`。路径必须经操作者明确核对，未确认前不启动。仅测 TXT 可把模型指向全新的空目录，避免加载/下载；真正 OCR 必须用已校验模型与对应运行时。

原生 Mac 用新的 support 隔离，但部分 WebKit 偏好仍共享；不要改历史任务或全局主题来测试。Windows 原生隔离按第 4.1 节，不照抄 Mac 变量。原生文件框、取消/再开、表格四主题、完整 ZIP 保存、刷新、关闭、进程释放各留证。原始截图/日志保留在忽略目录，公开只提交脱敏摘要。

## 6. MLX 已完成内容与待验证边界

详细算法、基准命令与指标解释见 [MLX_PERFORMANCE.md](../MLX_PERFORMANCE.md)。核心改动：每个 token 的现有阻塞 `.item()` 完成后释放过期 `output/logits` 引用；只有 `mx.get_cache_memory() > 1 GiB` 时清理闲置缓存。不碰活跃权重/KV、不加线程、不提高全局 wired/memory/cache limit、不改图像或生成算法。

| 已完成证据 | 不能推导出的结论 |
| --- | --- |
| M3 Max / 36 GiB，安装包 Python / MLX 0.29.3，Metal GPU | 不是 Neural Engine；也不代表所有 Mac 加速必须用 MLX |
| 五张合成图，交替 AB/BA，两轮共 20 次/10 对，完整 token/文字/停止诊断相同 | 不是所有文档准确率保证；最长 370 tokens，未实测触发重复截断 |
| 该组合累计 604.77 → 373.98 秒，减少 38.16% | 不是浏览器端到端；不含首次模型加载；小图首字后阶段略慢，不保证全部输入加速 |
| 末尾闲置缓存由约 9.19–21.77 GB 降至 0.44–2.24 GB | 1 GiB 是软触发，不是硬内存上限；活跃峰值仍约 17.4 GB，最低硬件要求未降低 |
| 源码真实浏览器两张图片导入/OCR/阅读/ZIP/自动卸载/关闭通过 | 未替换安装 App、未更新 DMG/EXE；不等于 Windows 或长 PDF 通过 |

基准参考提交 `ce8b0392f72a282071a6b451612ffe709924c51f`，优化提交 `d501ffde54f6d7c07dfd8a3e84be8142048b7183`，Windows UTF-8 测试修复 `d23aa16033aa0a602d2977fab23fe647ebc11ec0`。不要再用默认编码读取中文源码（Windows cp1252 曾使 4 项测试失败）。

私有 report SHA-256 `60eebcfc51cfa36a837c4584aa692546c7df6d2af3151358f003548f73e91b78`。报告创建时 HEAD 还是基线，不能用其单一 `source_commit` 判断候选；逐文件 SHA 已与最终源码核对，详情见原文。本包不附原始报告/合成图片/截图/日志，需要时按脚本重新生成，或请用户决定是否另提供脱敏证据。

下一步优先是用户确认后的 **原生候选集成和实测**，不是盲目换算法/量化/降低 DPI。质量参数、终止/防重复、读取和导出结果必须保持；任何新优化都要先建立受控基线。

## 7. 打包、发布与回滚

正式入口和全部门禁见 [DEPLOYMENT.md](../DEPLOYMENT.md)。这里只列定位，不替代授权或操作前检查：

| 目标 | 入口 |
| --- | --- |
| 网页 | `npm run build` → `dist/standalone/` |
| Mac App | 先网页构建，再 `./mac-app/build-app.sh` |
| Mac DMG | `node scripts/build_identity.mjs --require-release`，再 `./mac-app/build-installer.sh` |
| Windows（Mac 交叉构建） | 先网页构建，再 `./windows/build-installer.sh`；需 NSIS |
| Windows（原生） | `.\windows\build-installer.ps1`；Node/Python/NSIS 按 Windows 文档，不绕过执行策略 |
| Mac 部署/回退 | `.venv/bin/python scripts/deploy_macos.py snapshot/install/rollback ...`；完整必填参数见 DEPLOYMENT |

当前构建脚本仍输出 **rc.2 同名包**。新优化候选必须先确认新版本范围，版本修改走 PR，禁止直接覆盖已有 rc.2 或复用其 tag。Mac `.app` / Windows stage 会被重建；旧产物先复制到 build 外并核对哈希，再构建。install 的 backup-dir 必须全新、与 Applications 同一文件系统，不能复用历史审计目录。

来源门禁要求干净源码、`HEAD == origin/main`、前端摘要匹配、包内 SOURCE_COMMIT 正确。ZIP 无 `.git`，不满足这些门禁；真正发布应重新 clone，不能创建假 Git 仓库、写假 SOURCE_COMMIT、移除 `--require-release` 或复制旧 dist。

Mac 回退只恢复经核对的 `previous.app`，以对应 `installed-manifest.json` 检查漂移；保护扫描/模型不迁移不覆盖。原机耐久回退点位于应用支持根的 `maintenance-backups/2026-10-22-local-preview/install-reader-fix/`，这只是历史定位，接手前检查确实存在且与记录一致，不复制到交接包或未经确认使用。Windows 回装保留的旧安装器，保留 `%LOCALAPPDATA%\MoxiOCRStudio`。App-only 回滚不能恢复已被误改的业务数据。

源码通过 revert PR 回退；不 force push、不移动旧 tag。候选异常按部署文档标撤回并保留历史包；未获得新候选发布授权，不创建 Release。本次交接只导出 Git 跟踪源码，不手工构建/交付/发布新安装器、不部署；既有 PR/main CI 仍自动构建 Windows 测试 artifact（保留 7 天），不属于新候选发行或实机验收，不随交接包分发。

## 8. 证据索引与历史故障定位

| 症状 / 议题 | 证据与接手重点 |
| --- | --- |
| Windows LNK 报 `HEUR:Trojan/LNK.Agent.b` | 历史停止快捷方式命中；当前源码已移除该 LNK/脚本启动方式。当前目标机未验，不能直接定性误报或保证已解决 |
| Windows `ERR_CONNECTION_REFUSED` | 历史 Edge 初始进程提前退出导致停服是定位线索；现心跳方案有 CPU 测试，仍需真实 Edge 冷/热启动、刷新、最小化/退出复验 |
| 原生点击选文件无反应 | Swift WKWebView 文件面板路径有历史修复；修改后必须测打开/取消/再开、多文件，不只测普通 Chrome |
| 完整 ZIP 导出使主页面“帧框加载已中断” | 现原生下载/保存路径已有合成文件验证；若复现查导航/下载代理和实际 ZIP 内容，别仅检查 API 200 |
| 重复识别/阅读修复 | `repetition.py`、`repair_results.py`、相关测试；读/写两版要区分，不能自动修用户历史结果 |
| 阅读深色白底浅字 | PR #7 CSS 修复，rc.2 双平台已打包；四主题需真视觉回归，不能只数 DOM 文字 |
| 模型常驻/高内存 | 队列/心跳/退出卸载与 MLX 闲置缓存是两层问题；检测 active/cache、进程和负载，不能把系统全部 swap 归因此 App |
| macOS sandbox / 输入法诊断 | 原生验证仍有历史诊断，未证明消除；按工单保留原始时间线，区分系统噪声和功能故障 |

主索引：维护铁律；README；CHANGELOG；DEPLOYMENT；MLX_PERFORMANCE；RC2_VALIDATION；LOCAL_PREVIEW_UPDATE；MODEL_DOWNLOAD_VALIDATION；WINDOWS_CODEX_HANDOFF；WINDOWS_TEST_REPORT_TEMPLATE。早期 LOCAL_VALIDATION、MAC_READER_VALIDATION 和 rc.1 文档仅供背景。若不同日期结论冲突，先定位**提交、包、平台、样本**，不要删掉失败记录。

## 9. 交接包边界与完整性

包由本次文档 PR 合并后的 `git archive` 导出，仅 Git 跟踪树；不递归压缩工作目录、不包含历史 `.git`，不包含 ignored/untracked。压缩包之外的 `.sha256` 和交付校验记录是本次生成的验证产物，不是项目业务数据。

接收方可用标准 ZIP 工具解压；验证 CRC、目录穿越/重复条目/链接、文件清单与来源、中文文件名和阅读入口。Git archive 的 ZIP 注释保存完整提交；用 Python 标准库只读查看（将路径替换为实际 ZIP）：

```sh
python3 -c 'import sys,zipfile; z=zipfile.ZipFile(sys.argv[1]); print("source:",z.comment.decode("ascii")); print("first_bad_entry:",z.testzip())' /实际路径/交接包.zip
```

Windows 用 `py -3.12` 替代 `python3`。`first_bad_entry: None` 只表示 CRC 无错，不证明代码安全或 App 可运行。包 hash 要与本次随包校验值比对；最终应用验收仍按对应工单。

本次只交接源码和文档；未向 DeepSeek 或其他服务发送模型/用户数据，没有改 App、端口、任务或公开资产。下一步工单在 [WORK_ORDERS.md](WORK_ORDERS.md)。
