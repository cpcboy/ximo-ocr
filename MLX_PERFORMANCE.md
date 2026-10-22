# Apple Silicon MLX 推理效率验证

状态：2026-10-22 源码候选，尚未更新已安装 App 或公开 rc.2 安装包。只使用本机合成样本和已校验模型；不扫描、上传或迁移用户业务文件。性能、输出一致性、浏览器验收与部署分别登记，未通过项不冒记完成。

## 研究结论与边界

- 此项目的 `LoJexLLM/Unlimited-OCR-MLX` 转换版使用 MLX，在 Apple Silicon 上通过 Metal GPU 执行。已安装 App 自带 MLX 0.29.3，实际探针为 `Device(gpu, 0)`、Metal 可用，无需用户另装框架，也不经过 LM Studio。MLX 不是所有 Mac 模型加速的唯一途径，本结论仅针对此模型/引擎；不声称使用 Neural Engine。
- 模型卡：[LoJexLLM/Unlimited-OCR-MLX](https://huggingface.co/LoJexLLM/Unlimited-OCR-MLX)；框架：[Apple MLX](https://github.com/ml-explore/mlx)、[统一内存](https://ml-explore.github.io/mlx/build/html/usage/unified_memory.html)、[惰性执行](https://ml-explore.github.io/mlx/build/html/usage/lazy_evaluation.html)。模型卡宣传速度不是本项目实测。
- [MLX 0.29.3 allocator](https://github.com/ml-explore/mlx/blob/v0.29.3/mlx/backend/metal/allocator.cpp) 的 `clear_cache()` 仅回收闲置缓冲，不改活跃权重/KV。`get_peak_memory()` 统计活跃内存峰值，不能拿它当闲置缓存或清理后的内存值。
- 本机 M3 Max / 36 GiB，既有系统内存压缩、交换和其他负载会影响计时；系统 swap 不能全部归因墨析。本次不终止其他程序、不改系统参数、不提高 MLX wired/memory/cache 全局限制。

## 最小实现

`backend/model_compat.py` 在现有每个 token 的阻塞 `.item()` 完成后，保留 KV 和选定 token，删除已经用完的 `output/logits` 引用，调用 `backend/mlx_performance.py`。只有闲置缓存超过 1 GiB 时才回收；小缓存继续复用。

这是安全点检查的**软触发阈值**，不是总内存/缓存硬上限：单次计算、prefill 和延后释放仍可超过阈值。视觉阶段活跃峰值仍可能约 17 GB，不能据此降低机器内存要求。操作仍在原扫描锁内，不增加清理线程；队列结束/关闭页面/退出 App 的卸载流程不变。

不改权重、精度、图片尺寸/切块、DPI、prompt、最大输出长度、temperature、注意力或矩阵计算内核、防重复/停止规则。Windows 的 NVIDIA/PyTorch 引擎不使用此模块，未做 Windows 推理提速宣传。

已拒绝或撤回的实验：

- 只计算最后一行 logits：可能从 GEMM 变为 GEMV，浮点结果路径改变，未纳入候选。
- 单 token MoE 排序捷径：小矩阵数值测试通过，但首对实测 75.01→84.56 秒，无稳定收益，已撤回。
- 只在首字后清一次缓存：两图四次输出一致，但大页后续闲置缓存仍重新增长到约 21.8 GB，改为阈值检查。不能把这些全部归因某一种中间缓冲。

## 可复现的隔离基准

固定模型修订 `267d7adcbcd3730fdffb1eefd70ef6f486fbfc92`，FP16 权重内容不变。使用**安装包的 Python / MLX 0.29.3**，不是开发虚拟环境的 MLX 0.31.2。基准源码为 `scripts/benchmark_mlx.py`，必须指定已完整校验的本地模型和全新输出目录；不下载、不读取生产任务。

```sh
PYTHONDONTWRITEBYTECODE=1 '/Applications/墨析 OCR 工作台.app/Contents/Resources/OCRStudioRuntime/python/bin/python3' \
  -u scripts/benchmark_mlx.py \
  --model-dir "$MODEL_DIRECTORY" --output "$NEW_BENCHMARK_DIRECTORY" \
  --paired --reference-commit ce8b0392f72a282071a6b451612ffe709924c51f --repeats 2
```

两个变量必须由操作者填入真实模型目录和不存在的私有验证目录；不复制整条命令去覆盖旧报告。脚本仅用于 Apple Silicon/macOS，合成图字体使用系统 Arial/STHeiti；不是跨平台 OCR 测试入口。

五张生成的合成图：英文段落、简单表格、语法/符号、600×600 中英混排、带网格表格/双栏页。两组使用完全相同的高精度设置：base 1024、tile 640、动态切块、temperature=0；基准最大长度 32768。真实网页验收保留界面默认最大长度 8192，两者输出均远未到上限，不将基准参数冒充 UI 默认值。

同一已加载模型，提取指定 Git 基线的原 `generate` 与当前候选进行对比，交替 AB/BA；每次计时前两边均同步并清闲置缓存。记录源码 SHA/文件哈希、模型修订、平台/MLX、输入 SHA、完整 token IDs/文字/停止诊断、各页耗时、首字耗时、首字后总耗时、active/cache、清理事件和卸载状态。首字后耗时包含清理和后处理，不是纯 decode 吞吐；监测开销包含在实验计时中。

每对必须输入、全部 token、文字、停止诊断完全相等，否则失败。报告只有全部完成才标 `passed / quality_gate_passed=true`，中断/清理失败标失败；异常后恢复临时方法并卸载模型。冷态首轮与暖态复测分别分析，不把首次清理之前的耗时差异直接归因本次代码，也不承诺任意文档永远提速。

## 2026-10-22 实测结果

五图双轮已完成，共 20 次识别、10 对比较；输入 SHA、完整 token、最终文字和停止诊断全部一致，且每图跨轮输出也相同、非空。报告 `status=passed`、`quality_gate_passed=true`。这证明本组输入与运行环境下输出无变化，不代表所有文档的通用准确率保证。最长输出 370 tokens；没有真实触发重复截断，长文档与所有停止边界未由此次实测覆盖。

下表为每图两轮的平均整页耗时，单位秒；总量为十次扫描累计，不包含模型首次加载。

| 合成输入 | 每次输出 token 数 | 基线均值 | 优化均值 | 耗时减少 |
| --- | --- | --- | --- | --- |
| 英文段落 900×1000 | 127 | 75.80 | 46.59 | 38.5% |
| 简单表格 900×1000 | 156 | 71.16 | 49.94 | 29.8% |
| 语法/符号 900×1000 | 164 | 87.20 | 57.01 | 34.6% |
| 中英混排小图 600×600 | 124 | 8.09 | 5.11 | 不作稳定提速结论，见下文 |
| 网格/双栏 1100×1400 | 370 | 60.14 | 28.34 | 52.9% |
| **本次组合累计** | — | **604.77** | **373.98** | **38.16%** |

四种较大图两轮整页和首字后耗时均下降。小图反例必须保留：首字后耗时两轮分别为 4.030→4.172、3.804→4.133 秒，略有退化；整页均值受首字阶段抖动影响，不能据此承诺小图提速。首次缓存清理前的首字差异不能直接归因本次调度，系统负载和冷暖态仍会影响结果。

每次扫描末闲置缓存：基线约 **9.19–21.77 GB**，优化约 **0.44–2.24 GB**（十进制）。活跃内存峰值最高两边仍约 **17.4 GB**，没有降低峰值或最低机器内存要求的证据。最后正常卸载后 active=20 bytes、cache=0；报告没有 error/cleanup_error。

### 证据与源码溯源

- 私有报告：`test-results/mlx-perf-20261022/bounded-cache/report.json`；SHA-256 `60eebcfc51cfa36a837c4584aa692546c7df6d2af3151358f003548f73e91b78`。五张合成输入及完整输出、逐轮时序均在同目录；不提交 Git 或安装包。
- 基线 `ce8b0392f72a282071a6b451612ffe709924c51f`。报告生成开始时候选尚未提交，所以 `source_commit` 记录的是当时 HEAD/基线，**不是优化提交**；实际候选四文件内容与之后提交 `d501ffd` / `d23aa16` 完全一致，以报告逐文件 SHA 为准。
- `scripts/benchmark_mlx.py`：`50dab6d8516834b6ae69e3581f13be970945b3525d1e8ee01c8cebe0fc035e32`。
- `backend/model_compat.py`：`35cc06da545b172ae32a50d3e678032681722068c40cf1dd06220b4a49a5a839`。
- `backend/mlx_performance.py`：`cdb2d5ee9d416e2b53ba0ec159b421735fefb9fafa37a539d4e5a6a49a42d2b3`。
- 未改动的 `backend/engine.py`：`cd51653576bdb27ac5fc1bc05952df618a846f3ebab9681b69cda2dd18b58e64`。
- 独立 reviewer 实际重算十对/各轮数值、核对五图和四源码 hash、基线 Git blob、卸载状态，通过，新增 P0/P1/P2=0。所有临时证据保存在忽略目录，不包含业务扫描。

## 真实浏览器隔离验证

使用 Codex 内置浏览器访问 `http://127.0.0.1:3000/`，当前提交 `d23aa16` 构建前端、源码后端配合安装包 Python/MLX 0.29.3。服务临时绑定原本空闲的本机 3000/18765；专用 `OCR_STUDIO_SUPPORT_DIR` / `OCR_STUDIO_DATA_DIR` 指向 `test-results/mlx-perf-20261022/ui/support/`，`PYTHONDONTWRITEBYTECODE=1`，模型目录只读使用既有已校验权重；没有启动已安装 App、读取历史扫描或发起模型下载。

实测路径：真实文件选择器一次选取 paragraph/grid-columns 两图 → 两任务串行识别完成 → 点击阅读、表格/双栏原图与正文对照可读 → 返回工作台 → 点击“完整结果包”实际下载 ZIP。任务元数据的后端每页识别耗时分别为 58.83/25.77 秒（首任务可能含模型加载，不含文件选择、上传、排队、渲染或下载），不是浏览器端到端耗时，**不是新的受控 A/B 性能数据**；两页文字与基准中的对应输出完全相同。页面显示模型“待加载”，辅助健康信息 `loaded=false`、`busy=false`、queue=0；后端 RSS 约281 MiB（单次观测，不能当 GPU 峰值）。

ZIP 有原图、页面预览、TXT/JSON/Markdown 共5项；CRC 全通过，原图字节与合成输入相同，JSON文字与已完成任务相同。浏览器下载后从 Downloads 移入下方私有证据目录。前后端日志无 traceback/5xx/error，浏览器 warn/error 数量0；Transformers 保留“未发现 PyTorch/TensorFlow/Flax”的提示，本引擎实际由 MLX 完成 OCR，未据此安装无关框架。外部 Origin、伪造 Host 的辅助只读请求均返回403；正常路径成功，无防护放宽。

私有证据（不提交/打包）：

- `test-results/mlx-perf-20261022/ui/evidence/completed.png`：两任务完成/模型待加载；SHA-256 `f1123faeffee2320493e52505e81aec4e17594b8be3ed246f22251ea89a51f15`。
- 同目录 `reader.png`：真实深色阅读视觉；SHA-256 `e4340cbc14225ca77c55fa4ec38b8c7c6f8e1f4ef27fabffead8945cf3945f22`。
- 同目录 `export-completed.png`、`grid-columns-package.zip`；ZIP SHA-256 `3cc621f7da67b32d2a95a6d01678d89a9a5e9dd8fe0e3a39ac187c4ad120e2b9`。
- 同目录 `backend.log` / `frontend.log`；独立证据复核结束后，临时 support（仅本次两条合成任务及其文件）移入用户废纸篓 `moxi-mlx-ui-support-20261022-1247`，可恢复。基准报告/输入和最终截图、ZIP、日志保留为本次审计证据，不进入仓库或安装包。

关闭验收页后，`/api/client/status` 返回 `connected=false`。随后停止本次启动的临时服务，原 PID 94172/94176 已不存在，3000/18765 无监听；没有停止任何其他应用，也没有遗留模型常驻进程。`/api/health` 本身会刷新客户端活动，不拿它验证“网页已断开”。

本节只证明源码候选的真实网页路径，不冒充新原生安装包、Windows、长 PDF 或正式生产验收；既有 rc.2 和现装 App 未包含本优化。

## Review、验证与部署门禁

- 代码自查及独立对抗 review：阈值版 P0/P1/P2=0。修复了实验工具方法恢复、失败状态、吞吐指标命名；补纯 CPU 阈值边界/连续调用、EOS/长度和原生成算法 AST 等价契约。
- 本机完整 pytest **68 passed**（5条既有 SWIG 弃用警告）、lint 通过、`npm test` 构建及 **11 项 Node 测试通过**；11项新增纯CPU测试、语法和 diff 空白检查通过。实际模型数值/性能不由这些单测替代。
- [PR #11](https://github.com/cpcboy/ximo-ocr/pull/11) 首轮 CI `39840098911` 暴露 Windows 测试按 cp1252 读取含中文源码的问题（4项失败）；Linux各测试步骤通过，但因矩阵 fail-fast 最终 cancelled，整轮不记成功。仅将新测试的6处读取明确为 UTF-8，经独立 review P0/P1/P2=0、本机11项复验后重跑；不改模型实现或放宽测试。修复提交 `d23aa16` 的 [CI 39840634398](https://github.com/cpcboy/ximo-ocr/actions/runs/39840634398) Linux、Windows 均成功；证据文档提交后的最终 PR/main CI 仍须单独核对。
- 上节真实浏览器隔离路径、自动卸载、下载包回读及临时服务端口/进程释放通过；独立 reviewer 实看三截图、比对 ZIP/任务/输入、检查日志和两平台 CI。1项计时表述 P2 已修正并复核关闭，最终证据/文档 P0/P1/P2=0，不以单元测试替代页面操作。
- 本次尚未得到替换已安装 App 的追加确认；先按既有流程 review → 文档 → PR/CI/合并。未确认不更新 `/Applications`、不发新公开安装包、不操作 Windows。
- 如果获确认，按 DEPLOYMENT.md 的原 snapshot/install/rollback 流程，先备份旧构建和现装 App，校验漂移与所有任务终态，再从合并后 clean main 构建/部署/真实复验。任何关键路径或数据保全失败则恢复旧 App，不改数据掩盖问题。

回滚：源码使用 revert PR；未部署无需 App 回滚。未来部署必须新建审计目录，按其 `previous.app` 和 `installed-manifest.json` 回退；不覆盖扫描、笔记或模型，不改历史 Release/tag。
