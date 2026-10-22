# 第三方组件与源码

墨析源代码按 AGPL-3.0-only 发布（见 `LICENSE`）。第三方代码仍适用各自原有许可证；模型不包含在安装包中。软件按原样提供，不附带质量或适销保证。

| 组件 | 使用方式与来源 |
| --- | --- |
| Python | Mac：CPython 3.11.17 portable（python-build-standalone 20261021）；Windows：官方 CPython 3.12.10 embeddable。PSF 许可及第三方声明保留于运行时。源码：https://www.python.org/downloads/source/ 、https://github.com/astral-sh/python-build-standalone |
| Node.js 22.23.2 | 官方二进制；LICENSE 原文随安装包保留。源码：https://nodejs.org/dist/v22.23.2/node-v22.23.2.tar.gz |
| PyMuPDF / MuPDF | PDF 渲染引擎。采用上游 AGPL 授权；未购买或声称持有商业授权。Mac PyMuPDF 1.28.0，Windows 1.26.4。源码和构建说明：https://github.com/pymupdf/PyMuPDF 、https://mupdf.com/releases/ 。精确 Python 发行源包可从 https://pypi.org/project/PyMuPDF/1.28.0/#files 与 https://pypi.org/project/PyMuPDF/1.26.4/#files 下载。 |
| React / Next.js / vinext / Lucide 与前端依赖 | 版本由 `package-lock.json` 锁定；构建时保留 npm 包的许可文件到 `frontend/third-party-licenses/`。包内缺漏时按 `third-party/licenses/index.json` 补充固定版本许可及来源说明；三项 MIT 声明缺正文的包使用明确标注的标准文本，不伪称上游原文。实际运行依赖缺少材料会阻止构建。 |
| MLX / Transformers / Pillow 等 Python 包 | 版本见 `mac-app/requirements-runtime.txt` 与 `windows/requirements-bootstrap.txt`；许可保留于 Python 的 `site-packages/*.dist-info`。源码地址与版权信息见相应包元数据。 |
| uv 0.12.0 | 首次配置 Windows AI 组件时从官方 GitHub 下载，先验证 SHA-256 再使用。Apache-2.0 OR MIT；https://github.com/astral-sh/uv/tree/0.12.0 |
| 模型 | Mac：https://huggingface.co/LoJexLLM/Unlimited-OCR-MLX；Windows：https://huggingface.co/baidu/Unlimited-OCR。各自许可和作者声明见模型仓库 README；文件修订和内容哈希见 `backend/models/`。不把模型与运行库的许可混为墨析自身许可。 |

当前版本对应的墨析完整源码和构建脚本在 https://github.com/cpcboy/ximo-ocr ，安装包内 `SOURCE_COMMIT` 指向具体提交。`UNCOMMITTED-` 前缀仅用于本机开发候选，禁止生产发布。重新分发时应保留项目和依赖许可、版权声明以及对应源码获取方式。
