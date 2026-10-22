# 变更记录

## 1.3.0 — 候选，尚未完成生产发布

### 功能

- Mac 首次使用可在 App 内下载 Unlimited-OCR MLX，保存到应用管理目录，无需预装 LM Studio。
- Windows 使用对应的 NVIDIA/PyTorch 模型；不提供无法运行的 MLX 权重。
- 展示下载进度、大小、路径与固定修订；支持暂停、断点续传、关闭重开续传、内容校验和修复。
- 保留原有阅读器、原生选文件与导出下载、队列完成自动卸载；不迁移历史扫描数据。

### 可靠性与安全

- 固定模型修订、逐文件哈希及完整收据；拒绝错位 Range、损坏文件、低磁盘和并发加载/下载。
- Windows 推理运行时采用版本化收据及真实导入探针，修复会重新探测和安装。
- 经用户确认加入本机 Origin/Host 校验，拒绝外部网页跨站请求，不扩大 CORS。
- Mac 改用随包携带的独立 Python/Node；Swift 和 MLX wheel 明确面向 macOS 14 最低系统。
- 构建关联源码摘要，拒绝旧前端；打包前后再次核对，未提交版本标记 `UNCOMMITTED`、禁止生产部署。
- Mac 部署器检查已合并干净源、已安装 App 漂移、正常退出、完整复制与可审计备份；不改业务数据。
- 用户确认按 AGPL-3.0-only 开源；随包保留项目、Node 和 npm/Python 依赖许可说明。
- Windows Git 检出固定许可文本时强制 LF，避免 CRLF 改变校验哈希；不降低哈希校验要求。
- Windows 安装器使用构建主机原生文件通配路径和显式 UTF-8，修复原生 NSIS 的混合路径分隔符失败并防止中文名称乱码；增加真实编译回归。

### 发布范围与回滚

Mac 需通过全量首次下载、真实图片 OCR、阅读/导出、退出进程验证后才能更新生产。Windows 安装包标记 candidate，仍需目标 Windows 10 / NVIDIA 电脑验收；CI/交叉构建不等同于实机验收。

当前证据和未完成项：[MODEL_DOWNLOAD_VALIDATION.md](MODEL_DOWNLOAD_VALIDATION.md)。
回滚只恢复旧 App/安装包，保留扫描数据与模型；按 [DEPLOYMENT.md](DEPLOYMENT.md) 核对漂移与备份，不直接推 main。
