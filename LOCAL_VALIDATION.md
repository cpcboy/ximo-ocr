# 当前源码的本机验证状态

验证日期：2026-07-29

在 macOS 源码环境中已经执行：

- `python3 -m py_compile backend/*.py windows/*.py`：通过
- `.venv/bin/python -m pytest -q`：10 项通过
- `npm run lint`：通过
- `node --test tests/rendered-html.test.mjs`：2 项通过
- Windows NSIS 安装内容规则：不创建 PowerShell 停止快捷方式
- 源码包检查：不包含模型权重、用户数据、`.env` 或构建缓存

尚未完成：

- v1.0.2 在真实 Windows 10 上的启动验证
- Edge 已打开/未打开两种场景
- 目标杀毒软件扫描
- NVIDIA 模型下载与真实 OCR
- 关闭窗口后的进程与显存释放验证

因此 v1.0.2 当前只能称为“修复候选版”，Windows Codex 必须完成
`WINDOWS_CODEX_HANDOFF.md` 中的实机验收后才能生成最终交付结论。
