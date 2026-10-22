# 墨析 OCR 工作台：Windows Codex 交接说明

先完整阅读 `AGENTS.md`、`MAINTENANCE_RULES.md` 和 `DEPLOYMENT.md`。唯一仓库为 https://github.com/cpcboy/ximo-ocr ，任何修复均走主题分支 → 独立 review/测试 → PR → 合并 → 发布；禁止直接在生产安装目录改代码。源代码按 AGPL-3.0-only 开源，用户扫描数据不上传。

## 交接目标

请在真实的 Windows 10 专业版 x64 电脑上检查、修复、测试并重新生成安装包。

当前源码版本标记为 **v1.3.0 candidate**。它尚未在目标 Windows 电脑上完成端到端验证，不能仅凭编译或 CI 成功就宣称完成。最终结论必须以目标电脑上的安装、杀毒软件、浏览器、进程、显存和真实 OCR 操作为准。1.0.1/1.0.2 的历史故障与修复背景保留在下文，不代表目标机器问题已经实测消失。

1.3.0 新增：固定模型清单与哈希、下载/加载互斥、完整 Range 校验、可恢复下载、运行时真实导入检查及重新安装修复、本机 Host/Origin 拦截、安装包来源摘要和许可文件。Windows 只提供 NVIDIA/PyTorch，不下载 Apple MLX 模型。当前验证边界见 `MODEL_DOWNLOAD_VALIDATION.md`。

## 用户最终需要的体验

1. 双击正常安装程序完成安装，不再触发 `Trojan/LNK.Agent.b`。
2. 从桌面或开始菜单启动“墨析 OCR 工作台”。
3. 应用窗口可以稳定访问 `http://127.0.0.1:3000/`，不能再出现 `ERR_CONNECTION_REFUSED`。
4. 设置页可以点击下载官方 Windows 模型和推理组件；模型不打进安装包。
5. 支持图片、PDF、文本、多页图片、ZIP；Office 文件在安装 LibreOffice 后可转换。
6. 关闭应用窗口后，前端、后端和模型都自动退出，释放内存和 NVIDIA 显存。
7. 卸载主程序时保留已经下载的模型与识别记录。

## 两次已知故障

### 1. 杀毒软件误报旧版停止快捷方式

证据：用户在原任务中提供的安全日志截图。公开源码不附用户原始截图。

命中路径是：

`...\Start Menu\Programs\墨析 OCR 工作台\停止后台服务.lnk`

旧版快捷方式直接以隐藏窗口和 `ExecutionPolicy Bypass` 调用 PowerShell；用户截图显示该 LNK 被启发式规则 `HEUR:Trojan/LNK.Agent.b` 命中，不能只凭截图判定其余文件均安全。v1.0.1 起源码已有这些修改：

- 不再创建“停止后台服务.lnk”。
- 不再把 PowerShell 脚本打入安装包。
- 主快捷方式只指向 `$INSTDIR\MoxiOCRStudio.exe`，不带可疑参数。
- 启停逻辑改为内置 `pythonw.exe + windows_launcher.py`。
- 升级安装时主动删除旧 LNK、`launch.ps1` 和 `stop.ps1`。

请不要通过添加杀毒软件排除项来掩盖问题。必须验证新版安装后没有旧快捷方式，并用目标电脑的杀毒软件重新扫描。

### 2. 安装后打开即显示 127.0.0.1 拒绝连接

证据：用户在原任务中提供的浏览器拒绝连接截图。公开源码不附用户原始截图。

高概率根因已经定位到 v1.0.1 的：

`windows/windows_launcher.py`

旧逻辑启动 Edge 后直接执行 `edge_process.wait()`。当 Edge 把新窗口交给已经存在的 Edge 进程时，初始进程会很快退出，启动器随即进入 `finally`，杀掉前端和后端，所以已经打开的浏览器显示 `ERR_CONNECTION_REFUSED`。

v1.0.2 候选源码已经改为：

- 后端增加 `/api/readyz`，启动器探活时不会伪造网页活动。
- 后端增加 `/api/client/status`，只读取网页连接状态，不更新时间。
- 前端仍每 1.6 秒访问 `/api/health` 作为心跳。
- 页面关闭时使用 `/api/client/disconnect` 通知后端。
- Windows 启动器不再等待 Edge 初始进程，而是等待网页真实心跳。
- Windows 环境的网页超时设为 90 秒，避免窗口最小化后浏览器定时器节流导致误停。
- 页面关闭后有 5 秒宽限，避免刷新页面时误杀服务。

这部分只在源码级测试过，必须在真实 Windows/Edge 上验证。

## 关键目录与文件

- `app/page.tsx`：前端主界面、1.6 秒心跳、页面关闭通知。
- `app/globals.css`：界面样式。
- `backend/app.py`：FastAPI、任务队列、健康检查、客户端生命周期、下载接口。
- `backend/windows_engine.py`：Windows PyTorch + CUDA 推理引擎。
- `backend/model_download.py`：官方模型和 Windows AI 组件下载、断点续传。
- `backend/documents.py`：图片、PDF、文本、ZIP、Office 转换。
- `windows/windows_launcher.py`：启动/停止前后端、打开 Edge、等待网页心跳。
- `windows/backend_bootstrap.py`：让内嵌 Python 找到安装后下载的 AI 包。
- `windows/installer.nsi`：NSIS 主安装器。
- `windows/launcher.nsi`：桌面入口 EXE。
- `windows/build-installer.ps1`：Windows 原生构建脚本。
- `tests/test_windows_launcher.py`：Windows 启动器与安装器约束测试。

## 模型与运行环境

- 官方模型：`baidu/Unlimited-OCR`
- 固定修订：`07dea832e22aefee32ad281d4b80551282e1c168`
- 模型页面：`https://huggingface.co/baidu/Unlimited-OCR`
- 模型文件不允许进入安装包。
- Windows 推理：PyTorch 2.10.0、torchvision 0.25.0、CUDA 12.8 wheel。
- 目标机需要 NVIDIA 显卡和可用驱动。
- 需要访问 Hugging Face、PyPI、PyTorch 官方 wheel 源及 GitHub；建议预留至少 18 GB。任何代理设置不应包含在日志或提交中。
- 模型约 6.68 GB，AI 运行库另行下载；只有文件校验和运行时真实导入均通过才显示配置完成。
- 模型位置：`%LOCALAPPDATA%\MoxiOCRStudio\models\Unlimited-OCR`
- AI 包位置：`%LOCALAPPDATA%\MoxiOCRStudio\ai-packages`
- 任务数据：`%LOCALAPPDATA%\MoxiOCRStudio\data`
- 日志：`%LOCALAPPDATA%\MoxiOCRStudio\logs`

## 构建前置条件

目标 Windows 构建机需要：

- Windows 10/11 x64
- Node.js 22
- Python 3.12 x64，且 `py -3.12` 可用
- NSIS 3.x，且 `makensis.exe` 可用
- 网络可访问 python.org、nodejs.org、PyPI

这些工具只用于构建。最终安装包会内置 Node 和 Python，用户运行时不需要预装。

## 建议检查命令

在源码根目录使用 PowerShell：

```powershell
npm ci
npm run lint
npm test

py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r windows/requirements-bootstrap.txt pytest httpx
.\.venv\Scripts\python.exe -m pytest -q
```

然后生成安装包：

```powershell
.\windows\build-installer.ps1
```

输出目录：

`build\windows\output\`

候选文件：`MoxiOCR-Windows-x64-1.3.0-candidate.exe` 和 `.sha256`。输出同名文件存在时会拒绝覆盖，先将仍需保留的旧包归档到 `build` 外。前端源码摘要必须与当前 checkout 一致；`SOURCE_COMMIT` 含 `UNCOMMITTED-` 的包仅供本机开发测试，不能发布生产。

## 真实 Windows 验收清单

### 安装和杀毒软件

- 卸载旧版后安装候选版。
- 安装期间、安装后分别执行杀毒扫描。
- 开始菜单不得出现“停止后台服务.lnk”。
- 主快捷方式必须只指向 `MoxiOCRStudio.exe`，不得调用 PowerShell。
- 安装目录不得包含 `.ps1`。
- 安装包不得包含 `.safetensors`、`.gguf`、`.pt`、`.pth` 模型权重。

### 启动稳定性

- Edge 完全关闭时启动一次。
- Edge 已经打开普通窗口时再启动一次。
- 连续启动两次，确认不会重复开启两套后台。
- 每次启动都要实际看到 OCR 页面和“后端在线”状态。
- 直接访问 `/api/readyz` 应返回 `{"status":"ok"}`。
- 刷新页面，后台不能退出。
- 最小化应用至少 2 分钟，后台不能退出。
- 关闭应用窗口后等待 10 秒，确认 `node.exe` 和内置 `python.exe` 已退出。

### 下载和推理

- 设置页显示 NVIDIA 硬件检测结果。
- 点击下载模型，确认目标是官方固定修订。
- 暂停后继续，确认断点续传。
- 下载中关闭窗口，重开后点击继续；确认不重复从头下载且最终哈希正确。
- 未下载完成时不能预加载；加载中/扫描队列未完成时不能修复覆盖模型。
- 运行库损坏/缺失的测试只在隔离数据目录进行，点击修复后必须重新安装并通过导入探针；不得破坏现有用户运行库来测试。
- 完整下载后重新启动，模型和 AI 包仍被发现。
- 用一张清晰图片完成 OCR。
- 用至少 3 页 PDF 完成 OCR。
- 关闭窗口后使用任务管理器和 `nvidia-smi` 确认显存释放。
- 外部网站 Origin 请求应返回 403；App 页面正常上传、下载、阅读、导出不受影响。不可为“修复”连接而放宽 CORS 或监听到 0.0.0.0。

### 数据与卸载

- 识别记录重启后仍存在。
- 卸载主程序后，`%LOCALAPPDATA%\MoxiOCRStudio` 中的模型和数据仍保留。
- 重装后可以继续使用已下载模型。

## 如果候选版仍然拒绝连接

先收集这些证据，不要盲改：

```text
%LOCALAPPDATA%\MoxiOCRStudio\logs\backend.log
%LOCALAPPDATA%\MoxiOCRStudio\logs\backend-error.log
%LOCALAPPDATA%\MoxiOCRStudio\logs\frontend.log
%LOCALAPPDATA%\MoxiOCRStudio\logs\frontend-error.log
```

然后检查：

```powershell
Get-NetTCPConnection -LocalPort 3000,18765 -ErrorAction SilentlyContinue
Get-Process node,python,pythonw,msedge -ErrorAction SilentlyContinue
Invoke-WebRequest http://127.0.0.1:18765/api/readyz -UseBasicParsing
Invoke-WebRequest http://127.0.0.1:3000/ -UseBasicParsing
```

判断时要区分：

- 后端未启动；
- 前端未启动；
- 端口被占用；
- 杀毒软件隔离了某个运行文件；
- Edge 窗口打开后启动器错误退出；
- 本机代理错误地接管了 127.0.0.1。

## 最终交付要求

Windows Codex 完成后请输出：

1. 最终安装包 `.exe`。
2. 同名 `.sha256` 文件。
3. 一份 `WINDOWS_TEST_REPORT.md`，记录目标电脑、显卡、杀毒软件、执行的测试和实际结果。
4. 明确说明模型没有被打进安装包。
5. 如仍有问题，附带原始日志和精确失败步骤，不要只写“可能是环境问题”。
6. 按维护铁律提供 PR、commit、review 清零记录、备份/漂移/部署/回滚证据和执行记录。日志在本机保留，公开提交只放脱敏摘要，不附用户路径、文档内容、凭据。
