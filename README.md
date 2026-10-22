# 墨析 · 本地 OCR 工作台

这是为 Unlimited-OCR 制作的本机网页工作台。macOS 版使用
`LoJexLLM/Unlimited-OCR-MLX`；Windows 安装版使用官方
`baidu/Unlimited-OCR` PyTorch 模型。文件、页面预览和识别结果都保存在本机，不调用外部 OCR 接口。

源码仓库：[cpcboy/ximo-ocr](https://github.com/cpcboy/ximo-ocr)。发行包只从该仓库的
[Releases](https://github.com/cpcboy/ximo-ocr/releases) 获取；没有发布的版本不能用本机候选构建替代。
项目采用 [AGPL-3.0-only](LICENSE)，第三方许可见 [THIRD_PARTY_NOTICES.md](THIRD_PARTY_NOTICES.md)。

1.3.0 当前验收状态见 [MODEL_DOWNLOAD_VALIDATION.md](MODEL_DOWNLOAD_VALIDATION.md)。Windows 始终明确区分候选包与目标 Windows 10 / NVIDIA 实机验收。

## 开始使用

2026-10-22 已公开 [v1.3.0-rc.2 候选预览版](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.2)：阅读配色修复已打入 Mac/Windows 新安装包，非正式版、非 Latest，不自动更新本机。新 DMG 已完成原生隔离阅读/导入/ZIP/退出验证；Windows 实机与完整图片 OCR 仍未验收。最新分发验证边界见 [rc.2 验证记录](RC2_VALIDATION.md)，校验与限制见 [rc.2 发行说明](RELEASE_CANDIDATE_v1.3.0-rc.2.md)。下文 rc.1 为历史批次，不代表 rc.2 状态。

1. macOS 请从“应用程序”打开“墨析 OCR 工作台”；开发环境也可双击
   `启动 OCR 工作台.command`。
2. 程序会在本机启动网页与识别服务。
3. 没有模型时，点击首页“下载模型”或右上角系统状态里的“下载模型与推理组件”；下载、完整校验完成后再扫描。无需预装 LM Studio。
4. 拖入文件，选择“高精度”或“快速”模式，然后等待逐页结果。
5. 表格类结果会自动显示为“排版预览”；切换到“原始文本”可查看或校对 HTML。
6. 可复制当前页的纯文字，并导出 TXT、Markdown、JSON 或完整 ZIP 结果包。
7. 任务队列全部完成后，模型会自动卸载并释放内存。关闭桌面 App 最后一个窗口会停止前后端及下载；网页单独关闭时按心跳检测卸载空闲模型。开发模式可双击 `停止 OCR 工作台.command` 停止全部本机服务。

首次加载 6.7 GB 模型时需要等待一小会儿。运行 OCR 时建议关闭 LM Studio 中已经加载的其他大模型，以免统一内存不足。

## Mac 加速与内存效率

Apple Silicon 安装版已内置 MLX，并使用 Metal GPU；无需额外安装 MLX 或启动 LM Studio。当前源码正在验证不改变识别参数的闲置缓存回收优化，现安装 App 和公开 rc.2 尚不包含此变更。它不量化权重、不降低图片分辨率、不截短输出；1 GiB 仅为闲置缓存回收触发阈值，不是总内存上限。实测、限制、回滚及安装状态见 [MLX_PERFORMANCE.md](MLX_PERFORMANCE.md)，不能把源码测试当作已安装版提速。

## 首次下载模型

| 平台 | 程序选择的模型 | 要求 |
| --- | --- | --- |
| Apple Silicon Mac | [LoJexLLM/Unlimited-OCR-MLX](https://huggingface.co/LoJexLLM/Unlimited-OCR-MLX) | M 系列芯片、macOS 14+；安装包内含独立 Python/MLX/Node，不依赖构建者的 Python。模型约 6.68 GB（界面按二进制显示约 6.22 GB），建议至少 8 GB 空闲磁盘。 |
| Windows x64 | [baidu/Unlimited-OCR](https://huggingface.co/baidu/Unlimited-OCR) | NVIDIA GPU 和兼容 CUDA 12.8 的驱动；另下载 PyTorch 等推理组件，建议至少 18 GB 空闲磁盘。Apple MLX 不支持 Windows。 |

- 下载由用户主动点击，不随启动自动下载。界面显示进度、文件名、保存目录和固定修订。
- 可以暂停、退出 App、重开后继续；`.part` 文件用于续传。网络失败不会把不完整权重当成可用模型。
- 模型来自固定 Hugging Face 修订，每个文件验证内容哈希，全部校验完成后才启用；模型自带的 Python 推理代码同样固定并校验。
- “校验 / 修复”会重新校验内容。Windows 还会重新检查运行组件能否导入、版本是否匹配，必要时重装到本应用专用目录。
- 下载时不要开始扫描；模型已载入、任务执行或排队中时不能下载覆盖它，先等待完成并卸载。
- 旧 Mac 用户的完整 LM Studio 模型仍可兼容使用；下载到墨析后优先使用墨析目录，不覆盖或删除旧模型。
- Mac 内置推理库损坏时重新安装墨析；Intel Mac 不提供 MLX 下载。网络不可用时保留断点，不通过关闭安全检查解决。

引擎会持续检查模型是否陷入重复生成，包括完全相同的短循环、长句循环，以及只改变编号的近似循环。发现异常后会提前停止并清理重复尾巴；网页会在该页底部显示处理提示。对于旧版已经导出的 JSON 结果，可使用 `backend.repair_results` 生成不覆盖原件的去重修复版。

## 内置阅读器

完成或部分完成的任务会显示“阅读”按钮。阅读器直接使用任务中已经保存的原页和
OCR 结果，不会重新加载识别模型，也不会另开后台服务。

- 支持原页、文字、左右对照三种布局，以及扫描双页显示。
- 支持整份文档快速搜索、页面导航、直接页码、键盘翻页和阅读进度；窄窗口会切换成可关闭的抽屉导航。
- 书签、页内笔记、最后阅读页、主题、字号、行距和显示偏好会随任务保存在本机。
- 图片支持缩放、适宽复位、旋转、全屏和 `Command/Ctrl + 滚轮` 缩放。
- 表格仍使用安全排版；复制时可选择清洁文字、原始 OCR、TSV 或 Markdown 表格，并可按当前原页/文字模式打印。
- 旧任务进入阅读器时会自动生成独立的清洁阅读版。重复片段只写入
  `reading_text`，原始 `text` 永远保留，可随时切换“原始 OCR”核对。
- 从阅读器选择“校对本页”会回到编辑工作台；人工修改页面后，旧的清洁阅读版会失效并在下次进入阅读器时重新整理。

进入阅读器时，如果模型已预先加载且当前没有任务，程序会主动卸载模型释放内存。
关闭最后一个应用窗口仍会停止前后端并释放模型。

## 支持的文件

- 图片：PNG、JPG、WEBP、BMP、GIF、HEIC/HEIF、多页 TIFF
- 文档：PDF、Word、Excel、PowerPoint、OpenDocument
- 文本：TXT、Markdown、CSV、JSON、XML、YAML、HTML、日志、RTF、EML
- 批量包：ZIP；会安全解压并扫描其中受支持的文件

扫描型 PDF、Office 文件和多页图片会先转换成逐页 PNG，再交给 Unlimited-OCR。文本型文件会直接读取，因此不浪费模型时间。

## 结果和隐私

- Mac 安装版根目录：`~/Library/Application Support/墨析 OCR 工作台/`。
- Windows 安装版根目录：`%LOCALAPPDATA%\MoxiOCRStudio\`。
- 安装版任务数据、日志分别在上述根目录的 `data/jobs/`、`logs/`；开发模式默认项目内 `data/`。
- Mac 独立模型：上述根目录的 `models/Unlimited-OCR-MLX/`；Windows：`models/Unlimited-OCR/`。
- 原件、结果、阅读笔记与模型留在本机；这些目录被 Git 忽略，安装器只复制代码和运行组件。
- 网页和后端只监听 `127.0.0.1`（端口 `3000` / `18765`），局域网其他设备无法直接访问。
- API 校验 Host 与浏览器 Origin，拒绝外部网页跨站操作；只接受现有 3000 端口本机前端，保留原生本机无 Origin 调用。

每个任务会保留原文件、逐页预览、逐页文字和导出文件。网页左侧删除任务时，这些本机副本会一并删除。

## 识别设置建议

- 普通文档：高精度、160 DPI、8K 输出。
- 表格或小字：高精度、220 DPI、16K 输出。
- 简单截图：快速、120 或 160 DPI、4K 输出。
- 页数很多的 PDF：先在“页码范围”填写 `1-10`、`12,15-20` 等范围。
- 模型的原生推荐指令是 `document parsing.`；除非有明确需求，一般不需要修改。

## 修复运行环境

安装版无法启动时，先查看应用数据目录的 `logs/`，然后从已验证发行包重装；不要删除扫描数据或关闭安全软件。
开发环境才使用 `安装或修复 OCR 工作台.command`，该脚本不是安装版的更新方式。

## Windows 10 安装版

Windows x64 安装包位于 `build/windows/output/`。安装包不包含模型；安装并启动后，在右上角“设置”中点击“下载模型与推理组件”，程序会从
`baidu/Unlimited-OCR` 官方仓库下载固定版本，并把模型保存在
`%LOCALAPPDATA%\MoxiOCRStudio\models\Unlimited-OCR`。

Windows 推理引擎需要 NVIDIA 显卡和可用的 NVIDIA 驱动。程序会在设置页显示硬件检测结果。图片、PDF、文本、多页图片和 ZIP 可直接处理；Word、Excel、PowerPoint 和 OpenDocument 转换需要 Windows 上另行安装 LibreOffice。

Mac 安装包也不内置 LibreOffice；Office 转换须在本机已安装可发现的 LibreOffice。模型下载成功不代表这项可选转换器已安装。

关闭应用窗口后，启动器会停止前后端进程并卸载模型。卸载主程序时，已经下载的模型与识别记录默认保留，重装后可继续使用。

## 开发与维护

先读 [AGENTS.md](AGENTS.md) 和 [MAINTENANCE_RULES.md](MAINTENANCE_RULES.md)。任何修改必须六步执行，先 PR、review 和测试，合并后才能发布，不允许只改已安装 App。

测试：`.venv/bin/python -m pytest -q`、`npm run lint`、`npm test`。安装依赖使用 `npm ci` 和项目隔离 Python 环境。
构建、来源校验、部署及回滚见 [DEPLOYMENT.md](DEPLOYMENT.md)，本次变化见 [CHANGELOG.md](CHANGELOG.md)。

## 本次候选交接

1.3.0 已合并源码并生成 Mac/Windows 候选安装包。2026-10-22 已按用户授权公开 [v1.3.0-rc.1 候选预览版](https://github.com/cpcboy/ximo-ocr/releases/tag/v1.3.0-rc.1)，标为 Pre-release、非 Latest。公开分发没有自动更新本机 App，也不代表全量模型 OCR 或 Windows 实机验收通过。

用户随后单独确认本机候选试用。首次来源 `c30850d3` 的 1.3.0 (6) 因深色阅读“白底浅字”回退，失败记录保留；追加授权的最小配色修复经 [PR #7](https://github.com/cpcboy/ximo-ocr/pull/7)、CI、合并后，已从 `b7d29292` 备份更新本机。安装版四主题可读性、原生文件选择、合成文本导入、完整 ZIP 及退出已复验，原扫描/模型清单不变，详见 [LOCAL_PREVIEW_UPDATE.md](LOCAL_PREVIEW_UPDATE.md)。公开安装包尚未替换，仍包含旧显示问题；本机修复不等于公开原包已修复，也不是全量 OCR/正式版验收或自动更新。

下载前先读 [候选发行说明](RELEASE_CANDIDATE_v1.3.0-rc.1.md)：Mac 仅适用 Apple Silicon/macOS 14+，Windows 图片 OCR 需要 NVIDIA GPU；两包不带模型。Mac 未 Developer ID 公证、Windows 未商业签名及目标杀毒验收，不要关闭防护。来源 SHA、安装包哈希、真实界面证据及未验收项见 [CANDIDATE_DELIVERY.md](CANDIDATE_DELIVERY.md)。

当前测试 Chrome 曾拦截 Windows EXE（`ERR_BLOCKED_BY_CLIENT`），Mac 大文件浏览器等待也未确认完成；独立下载哈希一致不代表这些浏览器路径通过。遇到拦截请停止并保留告警，不绕过安全检查。
